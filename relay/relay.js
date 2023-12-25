const net = require("node:net");
const BinaryParser = require("binary-parser").Parser;
// const { Buffer } = require('node:buffer');

const src_host = "127.0.0.1";
const src_port = 9011;

const dest_host = "";
const dest_port = 9511;

let reconnectTimeoutId;

function connectToServer() {
    const client = net.createConnection(src_port, src_host);

    client.on('connect', () => {
        console.log("connected to " + src_host + ":" + src_port);
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

    client.on("data", function (data) {
        // buf = Buffer.from(data);
        // console.log("poseX " + buf.readDoubleLE(44)); // poseX
        console.log(ClientLocalizationPoseStruct.parse(data));

        // if (node.datatype != "buffer") {
        //     data = data.toString(node.datatype);
        // }
        // if (node.stream) {
        //     var msg;
        //     if ((node.datatype) === "utf8" && node.newline !== "") {
        //         buffer = buffer + data;
        //         var parts = buffer.split(node.newline);
        //         for (var i = 0; i < parts.length - 1; i += 1) {
        //             msg = { topic: node.topic, payload: parts[i] };
        //             if (node.trim == true) { msg.payload += node.newline; }
        //             msg._session = { type: "tcp", id: id };
        //             node.send(msg);
        //         }
        //         buffer = parts[parts.length - 1];
        //     } else {
        //         msg = { topic: node.topic, payload: data };
        //         msg._session = { type: "tcp", id: id };
        //         node.send(msg);
        //     }
        // } else {
        //     if ((typeof data) === "string") {
        //         buffer = buffer + data;
        //     } else {
        //         buffer = Buffer.concat([buffer, data], buffer.length + data.length);
        //     }
        // }
    });

    client.on('data', (data) => {

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

const server = net.createServer();

server.listen(dest_port, (socket) => {
    console.log("Server listening on port" + dest_port);
});

server.on("connection", () => {
    console.log("new connection");
}); 