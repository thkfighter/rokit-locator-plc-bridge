const net = require("node:net");
const BinaryParser = require("binary-parser").Parser;
// const { Buffer } = require('node:buffer');

let frq_divisor = 3
let src_host = "127.0.0.1";
let src_port = 9011;
let dst_host = "";
let dst_port = 9511;
let payload;
let reconnectTimeoutId;

if (process.argv[2]) {
    frq_divisor = process.argv[2]
}

function connectToServer() {
    var count = 0;
    const client = net.createConnection(src_port, src_host);

    client.on('connect', () => {
        console.log("Connected to " + src_host + ":" + src_port);
        clearTimeout(reconnectTimeoutId);
    });

    const ClientLocalizationPoseStruct = new BinaryParser()
        .doublele("age")
        .doublele("timestamp")
        .uint64le("uniqueId")
        .int32le("state")
        .uint64le("errorFlags")
        .uint64le("infoFlags")
        .doublele("poseX")
        .doublele("poseY")
        .doublele("poseYaw")
        .doublele("covariance_1_1")
        .doublele("covariance_1_2")
        .doublele("covariance_1_3")
        .doublele("covariance_2_2")
        .doublele("covariance_2_3")
        .doublele("covariance_3_3")
        .doublele("poseZ")
        .doublele("quaternion_w")
        .doublele("quaternion_x")
        .doublele("quaternion_y")
        .doublele("quaternion_z")
        .uint64le("epoch")
        .doublele("lidarOdoPoseX")
        .doublele("lidarOdoPoseY")
        .doublele("lidarOdoPoseYaw");

    client.on("data", (data) => {
        // buf = Buffer.from(data);
        // console.log("poseX " + buf.readDoubleLE(44)); // poseX
        // console.log(ClientLocalizationPoseStruct.parse(data));
        if (++count == frq_divisor) {
            payload = data;
            broadcast(payload);
            count = 0;
        }

    });

    client.on("end", function () {
        console.log("disconnected from " + src_host + ":" + src_port);
        reconnectTimeoutId = setTimeout(connectToServer, 5000);
    });
    client.on("close", function () {

    });
    client.on("error", function (err) {
        console.error(err);
        reconnectTimeoutId = setTimeout(connectToServer, 5000);
    });
}
connectToServer();


// Function to broadcast data to all connected clients
function broadcast(data) {
    for (const client of Object.values(clients)) {
        if (client.writable) {
            client.write(data);
        } else {
            console.log(`Client ${client.id} is not writable.`);
            removeClient(client);
        }
    }
}

// Map to store connected clients
const clients = {};

// Create a TCP server
const server = net.createServer((socket) => {
    console.log('Client connected');

    // Assign a unique ID to the client
    socket.id = Date.now();
    clients[socket.id] = socket;

    // Handle incoming data from the client
    // socket.on('data', (data) => {
    //     console.log(`Received data from client ${socket.id}: ${data}`);
    //     // You can update the payload here based on the received data, if needed
    //     // For example: updatePayload(data);
    // });

    // Handle client disconnection
    socket.on('end', () => {
        console.log('Client disconnected');
        removeClient(socket);
    });
});

// Remove a client from the clients map
function removeClient(client) {
    delete clients[client.id];
}

// Start listening on port 9511
server.listen(dst_port, () => {
    console.log('Listening on port ' + dst_port);
});