// 1. Inject the subtitle box UI layer
const style = document.createElement('style');
style.innerHTML = `
  #isl-subtitle-box {
    position: fixed; bottom: 100px; left: 50%; transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.85); color: #f1c40f; font-size: 32px;
    font-weight: bold; padding: 15px 30px; border-radius: 10px; z-index: 2147483647;
  }
`;
document.head.appendChild(style);

const subtitleBox = document.createElement('div');
subtitleBox.id = 'isl-subtitle-box';
subtitleBox.innerText = "ISL-Connect: Connecting to Core Networks...";
document.body.appendChild(subtitleBox);

// 2. INITIALIZE WEBSOCKET ONLY ONCE (Points to your i5 laptop server)
const socket = new WebSocket("ws://192.168.0.61:8000/ws/v1/translate"); 

socket.onopen = () => {
    console.log("%c CONNECTED: Linked to i5 Server AI Engine! ", "background: #8e44ad; color: #fff; font-weight: bold;");
    subtitleBox.innerText = "ISL-Connect: Connected to Server. Loading Sandbox...";
};

socket.onmessage = (event) => {
    try {
        const response = JSON.parse(event.data);
        // Display the text returned from the i5 server inside your yellow subtitle box
        subtitleBox.innerText = response.text;
    } catch (err) {
        console.error("Failed to parse incoming server translation string: ", err);
    }
};

socket.onerror = (error) => {
    console.error("WebSocket Pipeline Error: ", error);
    subtitleBox.innerText = "ISL-Connect: Server Offline";
};

// 3. Create and append the invisible sandbox frame
const iframe = document.createElement('iframe');
iframe.src = chrome.runtime.getURL('sandbox.html');
iframe.style.display = 'none';
document.body.appendChild(iframe);

let trackerReady = false;
let frameCounter = 0;

// 4. Listen for incoming coordinate data calculated by the sandbox environment
window.addEventListener("message", (event) => {
  if (event.data.type === "TRACKER_READY") {
    trackerReady = true;
    subtitleBox.innerText = "ISL-Connect: System Active & Live!";
    console.log("%c SUCCESS: Sandbox Tracker Ready! ", "background: #2ecc71; color: #fff; font-size: 14px;");
    startFrameCaptureLoop();
  }
  
  if (event.data.type === "COORDINATES") {
    const coords = event.data.data;
    console.log(`SANDBOX DATA -> X: ${coords.x.toFixed(2)} | Y: ${coords.y.toFixed(2)}`);

    // Send the clean coordinates to the i5 server over the open pipeline
    if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ landmarks: coords }));
    }
  }
});

// 5. Capture Google Meet frames and extract raw transferrable pixel buffers
function startFrameCaptureLoop() {
  const videoElement = document.querySelector('video');
  
  if (videoElement && videoElement.readyState >= 2 && trackerReady) {
    frameCounter++;
    
    // Process every 3rd frame to optimize performance on your i3 processor
    if (frameCounter % 3 === 0) {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = videoElement.videoWidth || 640;
        canvas.height = videoElement.videoHeight || 480;
        const ctx = canvas.getContext('2d');
        
        // Draw the current video frame safely
        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
        const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        
        // Convert the structural image data array into an explicit transferrable ArrayBuffer
        const buffer = imgData.data.buffer;
        
        iframe.contentWindow.postMessage({
          type: "PROCESS_FRAME",
          width: canvas.width,
          height: canvas.height,
          buffer: buffer
        }, "*", [buffer]); // Passing the buffer array directly avoids serialization lag
        
      } catch (err) {
        console.warn("Frame extraction skipped due to canvas sync: ", err.message);
      }
    }
  }
  requestAnimationFrame(startFrameCaptureLoop);
}