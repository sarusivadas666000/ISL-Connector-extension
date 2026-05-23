import os
import json
import asyncio
import numpy as np  # Essential for structural matrix arrays
from fastapi import FastAPI, WebSocket
import uvicorn

# Force Keras to use TensorFlow backend
os.environ["KERAS_BACKEND"] = "tensorflow"
import keras

app = FastAPI()

# Global sequence buffer to hold consecutive frame landmarks over a timeline
sequence_buffer = []

print("Loading Custom Trained ISL Translation Model...")
try:
    # Load your local custom model weights and structural string labels
    isl_model = keras.saving.load_model("isl_model.h5")
    actions = np.load("labels.npy", allow_pickle=True)
    print(f"Model loaded successfully! Active Translation Classes:\n{actions}")
except Exception as e:
    print(f"Error loading model assets: {e}. Falling back to layout pipeline setup.")
    isl_model = None
    actions = []

@app.websocket("/ws/v1/translate")
async def websocket_endpoint(websocket: WebSocket):
    global sequence_buffer
    await websocket.accept()
    print("\n[CONNECTED] i3 Chrome Extension successfully linked to i5 Backend Server AI Engine!")
    
    # Reset tracking buffer values on every fresh tab/room connection connection state
    sequence_buffer = []
    
    try:
        while True:
            try:
                # 1. Receive MediaPipe coordinate matrix from i3 extension
                data = await websocket.receive_text()
                if not data:
                    continue
                    
                payload = json.loads(data)
                landmarks = payload.get("landmarks", [])
                
                # --- STEP 2 STRUCTURAL VALIDATION PROTECTION ---
                # Check that landmarks is an active list and contains exactly the 126 coordinates
                # (21 points * 3 dims [x,y,z] * 2 hands) required by the model input layer
                if isinstance(landmarks, list) and len(landmarks) == 126:
                    
                    # Accumulate features into our moving historical timeline array
                    sequence_buffer.append(landmarks)
                    sequence_buffer = sequence_buffer[-30:]  # Retain only the trailing 30 frames
                    
                    # Log the progress of buffer tracking on your terminal console
                    print(f"[BUFFER PROGRESS] Active sequence size matching: {len(sequence_buffer)}/30", end="\r")
                    
                    if len(sequence_buffer) == 30:
                        # 2. Preprocess incoming matrices to match the expected 3D LSTM architecture input tensor: (1, 30, 126)
                        input_tensor = np.array(sequence_buffer).reshape(1, 30, 126) 
                        
                        # 3. Run instant inference via the loaded custom neural network
                        prediction = isl_model.predict(input_tensor, verbose=0)[0]
                        
                        # Find the highest classification score element index mapping
                        predicted_idx = np.argmax(prediction)
                        confidence = prediction[predicted_idx]
                        
                        # Apply an accuracy threshold filter check to prevent errant phrase flashing
                        if confidence > 0.80:
                            predicted_text = actions[predicted_idx]
                            print(f"\n[PREDICTION MATCH] Action: {predicted_text} | Confidence: {confidence:.2f}")
                        else:
                            predicted_text = "Analyzing movement tracks..."
                        
                        # 4. Send translated text back to the i3 subtitle box
                        await websocket.send_json({
                            "text": str(predicted_text),
                            "type": "subtitle"
                        })
                    else:
                        # Send status information when accumulating frames to fill the window
                        await websocket.send_json({
                            "text": f"Glove Calibrating... ({len(sequence_buffer)}/30)", 
                            "type": "status"
                        })
                else:
                    # Capture formatting errors transparently without breaking out of your main loop
                    print(f"\n[WARN - SCHEMA MISMATCH] Array ignored! Expected list of 126 components, but got: {type(landmarks)} with length {len(landmarks) if isinstance(landmarks, list) else 'N/A'}")
                    await websocket.send_json({
                        "text": "Adjusting tracking window alignment...", 
                        "type": "status"
                    })
                    
            except json.JSONDecodeError:
                print("\n[WARN] Failed to parse string buffer data as valid JSON. Skipping frame object...")
                continue
            except Exception as loop_error:
                print(f"\n[LOOP HANDLING ERROR] Safe catch executed: {loop_error}")
                continue
                
    except Exception as e:
        print(f"\n[DISCONNECTED] Main socket handling link terminated: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass  # Suppress errors if the socket is already closed

if __name__ == "__main__":
    # Run server locally on port 8000; listens to external local network devices
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)