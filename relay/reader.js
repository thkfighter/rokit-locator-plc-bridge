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

const ClientControlModeDatagram = new BinaryParser()
    .endianess('little')
    .bit3("LASEROUTPUT")
    .bit3("ALIGN")
    .bit3("REC")
    .bit3("LOC")
    .bit3("MAP")
    .bit3("VISUALRECORDING")
    .bit3("EXPANDMAP")
    .bit11("Unused");

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
            var result;
            myEmitter.on("payload", (data) => {
                console.log("ClientControlModeDatagram");
                console.log("LSB--MSB ", data);
                result = ClientControlModeDatagram.parse(data.swap32());
                console.log("MSB--LSB ", data);
                console.log(result);
                for (const key in result) {
                    if (key == "Unused") {
                        continue;
                    }
                    const value = result[key];
                    if (ClientState[value]) {
                        result[key] = ClientState[value];
                    } else {
                        console.error(`No matching state found for ${value} in ClientState`);
                    }
                }
                console.log(result);
            });
            break;
        default:
            console.log('Invalid choice. Please select a valid option.');
            break;
    }
    connectToServer();

    rl.close();
});