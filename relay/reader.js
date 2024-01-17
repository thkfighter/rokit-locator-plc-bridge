const net = require("node:net");
const BinaryParser = require("binary-parser").Parser;
// const { Buffer } = require('node:buffer');
const readline = require('readline');
const EventEmitter = require('node:events');

const myEmitter = new EventEmitter();

let src_host = "172.17.0.1";
let src_port = 9090;
let reconnectTimeoutId;

if (process.argv[2]) {
    src_host = process.argv[2]
}

if (process.argv[3]) {
    src_port = process.argv[3]
}

// This does not work. Use console.log(data) to see the bytes order.
// const ClientControlModeDatagram = new BinaryParser()
//     .endianess('little')
//     .bit3("LASEROUTPUT")
//     .bit3("ALIGN")
//     .bit3("REC")
//     .bit3("LOC")
//     .bit3("MAP")
//     .bit3("VISUALRECORDING")
//     .bit3("EXPANDMAP")
//     .bit11("Unused");

const ClientControlModeDatagram = new BinaryParser()
    .uint32le("controlMode");
let ControlModeDict = {
    "LASEROUTPUT": 8,
    "ALIGN": 8,
    "REC": 8,
    "LOC": 8,
    "MAP": 8,
    "VISUALRECORDING": 8,
    "EXPANDMAP": 8
};
const ClientState = {
    0: 'INIT',
    1: 'READY',
    2: 'RUN',
    4: 'NOT_AVAILABLE',
};
const ClientLocalizationPoseDatagram = new BinaryParser()
    .endianess('little')
    .doublele("age")
    .doublele("timestamp")
    .uint64("uniqueId")
    .int32("state")
    .uint64("errorFlags")
    .uint64("infoFlags")
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
    .uint64("epoch")
    .doublele("lidarOdoPoseX")
    .doublele("lidarOdoPoseY")
    .doublele("lidarOdoPoseYaw");

const ClientSensorLaserDatagram = new BinaryParser()
    .endianess('little')
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
    .uint32('rangeArraySize')
    .array('ranges', {
        length: 'rangeArraySize',
        type: 'floatle'
    })
    .uint8('hasIntensities')
    .floatle('minIntensity')
    .floatle('maxIntensity')
    .uint32('intensityArraySize')
    .array('intensities', {
        length: 'intensityArraySize',
        type: 'floatle'
    });

function connectToServer() {
    const client = net.createConnection(src_port, src_host);

    client.on('connect', () => {
        console.log("Connected to " + src_host + ":" + src_port);
        clearTimeout(reconnectTimeoutId);
    });

    client.on("data", (data) => {
        myEmitter.emit("payload", data);
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

// Create readline interface
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

// Display menu
console.log('\nChoose a function:');
console.log('1. ClientLocalizationPoseDatagram');
console.log('2. ClientSensorLaserDatagram');
console.log('3. ClientControlModeDatagram');

rl.question('\nEnter your choice: ', (choice) => {

    // Parse and validate the choice
    choice = parseInt(choice);

    switch (choice) {
        case 1:
            myEmitter.on("payload", (data) => {
                console.log("ClientLocalizationPoseDatagram");
                console.log(ClientLocalizationPoseDatagram.parse(data));
            });
            break;
        case 2:
            myEmitter.on("payload", (data) => {
                console.log("ClientSensorLaserDatagram");
                console.log(ClientSensorLaserDatagram.parse(data));
            });
            break;
        case 3:
            var oct;
            myEmitter.on("payload", (data) => {
                console.log("ClientControlModeDatagram");
                oct = ClientControlModeDatagram.parse(data)["controlMode"].toString(8);
                // ControlModeDict.LASEROUTPUT = oct[oct.length - 1];
                // ControlModeDict.ALIGN = oct[oct.length - 2];
                // ControlModeDict.REC = oct[oct.length - 3];
                // ControlModeDict.LOC = oct[oct.length - 4];
                // ControlModeDict.MAP = oct[oct.length - 5];
                // ControlModeDict.VISUALRECORDING = oct[oct.length - 6];
                // ControlModeDict.EXPANDMAP = oct[oct.length - 7];
                ControlModeDict.LASEROUTPUT = ClientState[oct[oct.length - 1]];
                ControlModeDict.ALIGN = ClientState[oct[oct.length - 2]];
                ControlModeDict.REC = ClientState[oct[oct.length - 3]];
                ControlModeDict.LOC = ClientState[oct[oct.length - 4]];
                ControlModeDict.MAP = ClientState[oct[oct.length - 5]];
                ControlModeDict.VISUALRECORDING = ClientState[oct[oct.length - 6]];
                ControlModeDict.EXPANDMAP = ClientState[oct[oct.length - 7]];
                console.log(ControlModeDict);
            });
            break;
        default:
            console.log('Invalid choice. Please select a valid option.');
            break;
    }
    connectToServer();

    rl.close();
});