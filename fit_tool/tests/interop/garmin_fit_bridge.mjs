import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

const sdkPath = process.env.FIT_JS_SDK_PATH;
if (!sdkPath) {
    throw new Error("FIT_JS_SDK_PATH must point to the Garmin fit-javascript-sdk matching fit_tool.SDK_VERSION");
}

const sdk = await import(pathToFileURL(path.join(sdkPath, "src", "index.js")));
const { Decoder, Encoder, Profile, Stream } = sdk;

function dateFields(message) {
    const converted = { ...message };
    for (const key of ["timestamp", "startTime", "timeCreated", "localTimestamp"]) {
        if (converted[key] != null) {
            converted[key] = new Date(converted[key]);
        }
    }
    return converted;
}

function messagesFromFixture(fixture) {
    return [
        { mesgNum: Profile.MesgNum.FILE_ID, ...dateFields(fixture.fileId) },
        { mesgNum: Profile.MesgNum.EVENT, ...dateFields(fixture.events[0]) },
        ...fixture.records.map((message) => ({
            mesgNum: Profile.MesgNum.RECORD,
            ...dateFields(message),
        })),
        { mesgNum: Profile.MesgNum.EVENT, ...dateFields(fixture.events[1]) },
        ...fixture.laps.map((message) => ({
            mesgNum: Profile.MesgNum.LAP,
            ...dateFields(message),
        })),
        ...fixture.sessions.map((message) => ({
            mesgNum: Profile.MesgNum.SESSION,
            ...dateFields(message),
        })),
        { mesgNum: Profile.MesgNum.ACTIVITY, ...dateFields(fixture.activity) },
    ];
}

function selected(message, keys) {
    return Object.fromEntries(keys.map((key) => [key, message[key]]));
}

function normalizedMessages(messages) {
    return {
        fileId: selected(
            messages.fileIdMesgs[0],
            ["type", "manufacturer", "product", "serialNumber", "timeCreated"],
        ),
        events: messages.eventMesgs.map((message) =>
            selected(message, ["timestamp", "event", "eventType"])),
        records: messages.recordMesgs.map((message) =>
            selected(message, ["timestamp", "distance", "heartRate", "cadence", "power"])),
        laps: messages.lapMesgs.map((message) =>
            selected(
                message,
                ["messageIndex", "timestamp", "startTime", "totalElapsedTime", "totalTimerTime"],
            )),
        sessions: messages.sessionMesgs.map((message) =>
            selected(
                message,
                [
                    "messageIndex",
                    "timestamp",
                    "startTime",
                    "totalElapsedTime",
                    "totalTimerTime",
                    "sport",
                    "subSport",
                    "firstLapIndex",
                    "numLaps",
                ],
            )),
        activity: selected(
            messages.activityMesgs[0],
            ["timestamp", "numSessions", "totalTimerTime"],
        ),
    };
}

function generate(fixture) {
    const encoder = new Encoder();
    for (const message of messagesFromFixture(fixture)) {
        encoder.writeMesg(message);
    }
    return Buffer.from(encoder.close()).toString("base64");
}

function decode(base64) {
    const bytes = Buffer.from(base64, "base64");
    const integrity = new Decoder(Stream.fromBuffer(bytes)).checkIntegrity();
    const { messages, profileVersion, errors } = new Decoder(Stream.fromBuffer(bytes)).read({
        mergeHeartRates: false,
    });
    if (errors.length > 0) {
        throw new Error(`Garmin decoder errors: ${errors.map((error) => error.message).join("; ")}`);
    }
    return {
        integrity,
        profileVersion,
        messages: normalizedMessages(messages),
    };
}

const request = JSON.parse(fs.readFileSync(0, "utf8"));
if (request.operation === "generate") {
    process.stdout.write(JSON.stringify({ fitBase64: generate(request.fixture) }));
} else if (request.operation === "decode") {
    process.stdout.write(JSON.stringify(decode(request.fitBase64)));
} else {
    throw new Error(`Unknown operation: ${request.operation}`);
}
