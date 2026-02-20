import { useState, useRef, useEffect } from "react";
import { Upload, Loader2, BarChart3, CheckCircle2, Camera, X } from "lucide-react";
import "./QCLive.css";
// import { image } from "framer-motion/client";

type QCItem = {
  class: string;
  count: number;
  ratio: number;
  color: string;
};

type QCResult = {
  total_count: number;
  status: "PASS" | "FAIL";
  items: QCItem[];
  overlay_image?: string | null;
  image_url?: string;
  overlay_url?: string | null;
  created_at: string;
};



function App() {
  const [result, setResult] = useState<QCResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | undefined>();
  const [fileName, setFileName] = useState<string>("");
  const [cameraOn, setCameraOn] = useState(false);
  const isSubmitting = useRef(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);



  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (isSubmitting.current) return;   // ✅ กันซ้ำ
    isSubmitting.current = true;

    if (!e.target.files || !e.target.files[0]) {
      isSubmitting.current = false;
      return;
    }

    const file = e.target.files[0];
    const formData = new FormData();
    formData.append("file", file);

    setFileName(file.name);
    setPreviewUrl(URL.createObjectURL(file));
    setLoading(true);
    setResult(null);

    try {
      const res = await fetch("http://127.0.0.1:8000/qc", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed");
      const data: QCResult = await res.json();
      setResult(data);
    } catch (error) {
      console.error("Upload error:", error);
      alert("Failed to process image. Please try again.");
    } finally {
      setLoading(false);
      isSubmitting.current = false;
    }
  };
  /* ===============================
   CAMERA CONTROL
    =============================== */
  const openCamera = async () => {
    // ✅ ถ้ามี stream อยู่แล้ว ไม่ต้องเปิดใหม่
    if (streamRef.current) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: false,
      });

      streamRef.current = stream;
      setCameraOn(true);
    } catch (err) {
      console.error(err);
      alert("ไม่สามารถเปิดกล้องได้");
    }
  };

  const closeCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    setCameraOn(false);
  };

  const captureFromCamera = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    if (isSubmitting.current) return;

    isSubmitting.current = true;
    setLoading(true);
    setResult(null);

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // canvas.width = 640;
    // canvas.height = 640;
    // ctx.drawImage(video, 0, 0, 640, 640);

    const videoWidth = video.videoWidth;
    const videoHeight = video.videoHeight;

    canvas.width = videoWidth;
    canvas.height = videoHeight;

    ctx.drawImage(video, 0, 0, videoWidth, videoHeight);



    const blob = await new Promise<Blob | null>(resolve =>
      canvas.toBlob(resolve, "image/jpeg")
    );

    if (!blob) return;

    const formData = new FormData();
    formData.append("file", blob, "camera.jpg");

    setPreviewUrl(URL.createObjectURL(blob));
    setFileName("Webcam Capture");

    try {
      const res = await fetch("http://127.0.0.1:8000/qc", {
        method: "POST",
        body: formData,
      });

      const data: QCResult = await res.json();
      setResult(data);
    } catch (err) {
      alert("QC Failed");
    } finally {
      setLoading(false);
      isSubmitting.current = false;
    }
  };

  /* ✅ เพิ่ม useEffect ตรงนี้ */
  useEffect(() => {
    if (!cameraOn) return;
    if (!videoRef.current) return;
    if (!streamRef.current) return;

    videoRef.current.srcObject = streamRef.current;
    videoRef.current.play();

    return () => {
      videoRef.current?.pause();
    };
  }, [cameraOn]);


  useEffect(() => {
    console.log(
      "NOW (TH):",
      new Date().toLocaleString("th-TH", {
        timeZone: "Asia/Bangkok",
        hour12: false,
      })
    );
  }, []);

  function thaiTime(time?: string) {
    const date = time ? new Date(time) : new Date();

    return date.toLocaleString("en-GB", {
      timeZone: "UTC",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  }
  console.log(
    "NOW (TH):",
    new Date().toLocaleString("th-TH", {
      timeZone: "UTC",
      hour12: false,
    })
  );

  //==========================Upload image==========================
  return (
    <div className="qc-app">
      {/* Main Content */}
      <main className="qc-main">
        <div className="qc-container">
          <div className="qc-grid">
            {/* Left Panel - Upload Section */}
            <div className="qc-left-panel">
              {/* Upload Card */}
              <div className="qc-card">
                <div className="qc-card-header">
                  <h2 className="qc-card-title">Image Upload</h2>
                </div>
                <div className="qc-card-body">
                  <label className="qc-upload-zone">
                    <Upload className="qc-upload-icon" size={40} strokeWidth={2} />
                    <p className="qc-upload-title">
                      Select File to Upload
                    </p>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleUpload}
                      className="qc-upload-input"
                    />
                  </label>
                </div>
              </div>

              {/* CCTV Camera Card */}
              {/* <div className="qc-card">
                <div className="qc-card-header">
                  <h2 className="qc-card-title">CCTV Camera</h2>
                </div>

                <div className="qc-card-body">
                  {!cameraOn && (
                    <div className="qc-upload-zone">
                      <Camera className="qc-upload-icon" size={40} strokeWidth={2} />
                      <p className="qc-upload-title">
                        Open CCTV Camera
                      </p>
                      <p className="qc-upload-description">
                        Live camera feed for real-time inspection
                      </p>
                      <p className="qc-upload-description">
                        Resolution: 640 × 640
                      </p>

                      <button
                        className="qc-btn primary"
                        onClick={() => setCameraOn(true)}
                      >
                        Open Camera
                      </button>

                    </div>
                  )}

                  {cameraOn && (
                    <div className="qc-camera-zone">
                      <img
                        src={`http://localhost:8000/cctv?t=${Date.now()}`}
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                      />


                      <div className="qc-camera-actions">
                        <button
                          onClick={async () => {
                            if (isSubmitting.current) return;
                            isSubmitting.current = true;

                            try {
                              setLoading(true);
                              setResult(null);

                              const res = await fetch("http://127.0.0.1:8000/qc/camera", {
                                method: "POST",
                              });

                              if (!res.ok) throw new Error("Camera QC failed");

                              const data: QCResult = await res.json();

                              setResult(data);

                              // ✅ เอารูปจากกล้องไปโชว์ที่ Image Preview
                              if (data.image_url) {
                                setPreviewUrl(data.image_url);
                                setFileName("CCTV Capture");
                              }
                            } catch (err) {
                              console.error(err);
                              alert("Failed to capture image");
                            } finally {
                              setLoading(false);
                              isSubmitting.current = false;
                            }
                          }}
                        >
                          Capture & QC
                        </button>


                        <button
                          className="qc-btn danger"
                          onClick={() => setCameraOn(false)}
                        >
                          <X size={16} /> Close Camera
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div> */}

              {/* ==========================Camera==========================   */}
              <div className="qc-card">
                <div className="qc-card-header">
                  <h2 className="qc-card-title">Computer Camera</h2>
                </div>

                <div className="qc-card-body">
                  {!cameraOn && (
                    <div className="qc-upload-zone">
                      <Camera className="qc-upload-icon" size={40} />
                      <p className="qc-upload-title">Open Computer Camera</p>

                      <button className="qc-btn primary" onClick={openCamera}>
                        Open Camera
                      </button>
                    </div>
                  )}

                  {cameraOn && (
                    <div className="qc-camera-zone">
                      <video
                        ref={videoRef}
                        autoPlay          // ✅ ต้องมี
                        playsInline
                        muted
                        style={{
                          width: "100%",
                          height: "360px",
                          objectFit: "cover",
                          background: "#000",
                        }}
                      />

                      <div className="qc-camera-actions">
                        <button onClick={captureFromCamera}>
                          Capture & QC
                        </button>

                        <button className="qc-btn danger" onClick={closeCamera}>
                          <X size={16} /> Close Camera
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <canvas ref={canvasRef} style={{ display: "none" }} />


              {/* Preview Card */}
              {previewUrl && (
                <div className="qc-card">
                  <div className="qc-card-header">
                    <h3 className="qc-card-title">Image Preview</h3>
                  </div>
                  <div className="qc-card-body">
                    <div className="qc-preview-image">
                      <img
                        src={previewUrl}
                        alt="Preview"
                        className="qc-image"
                      />
                    </div>
                    <div className="qc-preview-info">
                      <p className="qc-info-item">
                        <span className="qc-info-label">File Name:</span> {fileName}
                      </p>
                      <p className="qc-info-item">
                        <span className="qc-info-label">Upload Time:</span>{" "}
                        {result ? thaiTime(result.created_at) : "-"}
                      </p>
                      <p className="qc-success-message">
                        <CheckCircle2 size={14} />
                        Image processed successfully
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Right Panel - Results Section */}
            <div className="qc-right-panel">
              {/* Loading State */}
              {loading && (
                <div className="qc-loading">
                  <Loader2
                    size={56}
                    className="qc-loading-spinner"
                    strokeWidth={2.5}
                  />
                  <p className="qc-loading-title">
                    Processing Request
                  </p>
                  <p className="qc-loading-text">
                    Analyzing image data. Please wait...
                  </p>
                  <div className="qc-loading-bar">
                    <div className="qc-loading-progress"></div>
                  </div>
                </div>
              )}

              {/* Results */}
              {result && !loading && (
                <div className="qc-results">
                  {/* Overlay Result Image */}
                  {result.image_url && result.overlay_url && (
                    <div className="qc-card">
                      <div className="qc-card-header">
                        <h2 className="qc-card-title">AI Segmentation Result</h2>
                      </div>

                      <div className="qc-preview-container">
                        <div className="qc-preview-overlay-wrapper">
                          {/* รูปต้นฉบับ */}
                          <img
                            src={result.image_url}
                            alt="Original"
                            className="qc-image"
                          />

                          {/* รูป Overlay */}
                          <img
                            src={result.overlay_url}
                            alt="Overlay"
                            className="qc-overlay-image"
                          />
                        </div>
                      </div>

                    </div>
                  )}

                  {/* Analysis Summary Card */}
                  <div className="qc-card">
                    <div className="qc-card-header">
                      <h2 className="qc-card-title">Analysis Summary</h2>
                    </div>
                    <div className="qc-card-body">
                      <div className="qc-summary-grid">
                        {/* Total Weight */}
                        <div className="qc-summary-box">
                          <p className="qc-summary-label">Total Count</p>
                          <div className="qc-summary-value-wrapper">
                            <p className="qc-summary-value">
                              {result.total_count}
                            </p>
                            <p className="qc-summary-unit">items</p>
                          </div>
                          <p className="qc-summary-meta">
                            Measured at: {thaiTime(result.created_at)}
                          </p>
                        </div>

                        {/* Quality Status */}
                        <div className="qc-summary-box">
                          <p className="qc-summary-label">Quality Status</p>
                          <div
                            className={`qc-status-badge ${result.status === "PASS"
                              ? "qc-status-pass"
                              : "qc-status-fail"
                              }`}
                          >
                            {result.status === "PASS" ? "PASS" : "FAIL"}
                          </div>


                          <p className="qc-status-description">
                            {result.status === "PASS"
                              ? "Product meets quality standards"
                              : "Product requires inspection"}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Detailed Composition Report */}
                  <div className="qc-card">
                    <div className="qc-card-header qc-card-header-with-icon">
                      <h2 className="qc-card-title">Detailed Composition Report</h2>
                      <BarChart3 className="qc-header-icon" size={20} strokeWidth={2} />
                    </div>

                    <div className="qc-table-wrapper">
                      <table className="qc-table">
                        <thead>
                          <tr>
                            <th>Classification Category</th>
                            <th>Count (items)</th>
                            <th>Distribution Percentage</th>
                          </tr>
                        </thead>

                        <tbody>
                          {result.items.map((item, i) => (
                            <tr key={i}>
                              {/* ===== Class + Color ===== */}
                              <td>
                                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                  <span
                                    className="qc-color-dot"
                                    style={{ backgroundColor: item.color }}
                                  />
                                  <span className="qc-table-class">{item.class}</span>
                                </div>
                              </td>


                              {/* ===== count ===== */}
                              <td>
                                <span className="qc-table-count">{item.count}</span>
                              </td>
                              <td>
                                <div className="qc-progress-wrapper">
                                  <span className="qc-progress-percentage">
                                    {item.ratio}%
                                  </span>

                                  <div className="qc-progress-bar">


                                    <div
                                      className="qc-progress-fill"
                                      style={{
                                        width: `${item.ratio}%`,
                                        backgroundColor: item.color
                                      }}
                                    />

                                  </div>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>

                        <tfoot>
                          <tr>
                            <td className="qc-table-footer">Total</td>
                            <td className="qc-table-footer">{result.total_count}</td>
                            <td className="qc-table-footer">100%</td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>

                  </div>
                </div>
              )}

              {/* Initial State */}
              {!loading && !result && !previewUrl && (
                <div className="qc-empty-state">
                  <div className="qc-empty-icon-wrapper">
                    <BarChart3 className="qc-empty-icon" size={40} strokeWidth={2} />
                  </div>
                  <p className="qc-empty-title">No Analysis Available</p>
                  <p className="qc-empty-text">
                    Please upload an image to begin quality control analysis
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>


    </div>
  );
}

export default App;