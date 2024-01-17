// Module import
const BinaryParser = require("binary-parser").Parser;

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

// Prepare buffer to parse.
const buf = Buffer.from("00FF58D1", "hex");

// Parse buffer and show result
console.log(ClientControlModeDatagram.parse(buf));