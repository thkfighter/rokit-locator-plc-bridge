const net = require("node:net");
const BinaryParser = require("binary-parser").Parser;
// const { Buffer } = require('node:buffer');
const readline = require('readline');

let frq_divisor = 3
//let src_host = "192.168.8.7";
let src_host = "172.17.0.1";
let src_port = 9090;
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

    const ClientLocalizationPoseDatagram = new BinaryParser()
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

    // const ClientSensorLaserDatagram = new BinaryParser()
    //     .uint16('scanNum')
    //     .doublele('time_start', { assert: (val) => val >= 0 && val <= 1e12 })
    //     .uint64('uniqueId')
    //     .doublele('duration_beam', { assert: (val) => val >= 0 && val <= 1e12 })
    //     .doublele('duration_scan', { assert: (val) => val >= 0 && val <= 1e12 })
    //     .doublele('duration_rotate', { assert: (val) => val >= 0 && val <= 1e12 })
    //     .uint32('numBeams', { assert: (val) => val >= 0 && val <= 100000 })
    //     .floatle('angleStart', { assert: (val) => val >= -2 * Math.PI && val <= 2 * Math.PI })
    //     .floatle('angleEnd', { assert: (val) => val >= -2 * Math.PI && val <= 2 * Math.PI })
    //     .floatle('angleInc', { assert: (val) => val >= -2 * Math.PI && val <= 2 * Math.PI })
    //     .floatle('minRange', { assert: (val) => val >= 0 && val <= 1e4 })
    //     .floatle('maxRange', { assert: (val) => val >= 0 && val <= 1e4 })
    //     .array('ranges', {
    //         length: 'uint32',
    //         type: 'floatle',
    //         assert: (val) => val >= -1e4 && val <= 1e4
    //     })
    //     .uint8('hasIntensities')
    //     .floatle('minIntensity')
    //     .floatle('maxIntensity')
    //     .array('intensities', {
    //         length: 'uint32',
    //         type: 'floatle'
    //     });

    const ClientSensorLaserDatagram = new BinaryParser()
        .uint16('scanNum')
        .doublele('time_start')
        .uint64('uniqueId')
        .doublele('duration_beam')
        .doublele('duration_scan')
        .doublele('duration_rotate')
        .uint32('numBeams')
        .floatle('angleStart')
        .floatle('angleEnd')
        .floatle('angleInc')
        .floatle('minRange')
        .floatle('maxRange')
        .array('ranges', {
            length: 'uint32',
            type: 'floatle',
            assert: (val) => val >= -1e4 && val <= 1e4
        })
        .uint8('hasIntensities')
        .floatle('minIntensity')
        .floatle('maxIntensity')
        .array('intensities', {
            length: 'uint32',
            type: 'floatle'
        });

    client.on("data", (data) => {
        // buf = Buffer.from(data);
        // console.log("poseX " + buf.readDoubleLE(44)); // poseX
        // console.log(ClientLocalizationPoseDatagram.parse(data));
        console.log(ClientSensorLaserDatagram.parse(data));

        // if (++count == frq_divisor) {
        //     payload = data;
        //     broadcast(payload);
        //     count = 0;
        // }

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