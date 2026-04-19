const express = require("express");
const multer = require("multer");
const crypto = require("crypto");
const QRCode = require("qrcode");
const path = require("path");
const fs = require("fs");

const app = express();
const PORT = 3000;

// Serve uploaded files
app.use("/uploads", express.static("uploads"));

// Storage config
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, "uploads/");
  },
  filename: (req, file, cb) => {
    cb(null, Date.now() + "-" + file.originalname);
  },
});

const upload = multer({ storage });

// Fake DB (later replace with MongoDB)
let documents = {};

// 📌 Upload Route
app.post("/upload", upload.single("file"), async (req, res) => {
  const filePath = req.file.path;

  // Generate hash
  const fileBuffer = fs.readFileSync(filePath);
  const hash = crypto.createHash("sha256").update(fileBuffer).digest("hex");

  // Save mapping
  documents[hash] = filePath;

  // IMPORTANT: Use your IP instead of localhost for mobile scanning
  const url = `http://192.168.1.5:${PORT}/verify/${hash}`;

  // Generate QR
  const qr = await QRCode.toDataURL(url);

  res.send({
    message: "Uploaded successfully",
    hash,
    verifyLink: url,
    qr,
  });
});

// 📌 Verify Route
app.get("/verify/:hash", (req, res) => {
  const hash = req.params.hash;

  if (documents[hash]) {
    res.send(`
      <h1> Document Verified</h1>
      <p>This document is ORIGINAL</p>
    `);
  } else {
    res.send(`
      <h1> Invalid Document</h1>
      <p>This document may be TAMPERED</p>
    `);
  }
});

app.listen(PORT, () => console.log("Server running on port " + PORT));