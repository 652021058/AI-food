import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
from ultralytics import YOLO
import cv2
import os
import threading

# --- ตั้งค่า Path ของโมเดลทั้งหมด ---
MODEL_CONFIGS = {
    "Potato Model": {
        "path": r"D:\I-Tail\AI-food_production\potato.pt",
        "color": "#ff8b17",   # 🔵 น้ำเงิน (เปลี่ยนจากฟ้า)
        "label": "🥔 Potato"
    },
    "Peas Model": {
        "path": r"D:\I-Tail\AI-food_production\peas.pt",
        "color": "#27ae60",   # 🟢 เขียว (คงเดิม)
        "label": "🫛 Peas"
    },
    "Carrot Model": {
        "path": r"D:\I-Tail\AI-food_production\carrot.pt",
        "color": "#2260ff",#2260ff   # 🟠 ส้ม (เปลี่ยนจากน้ำเงิน)
        "label": "🥕 Carrot"
    }
}


class QCInspectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("QC Inspection System: Triple AI Model Counter")
        self.root.geometry("1300x800")
        self.root.state('zoomed')

        # สีหลัก
        self.colors = {
            "bg_sidebar":  "#1a252f",
            "bg_panel":    "#2c3e50",
            "bg_main":     "#ecf0f1",
            "text_light":  "#ffffff",
            "text_muted":  "#95a5a6",
            "accent_potato": "#2260ff",   # 🔵 น้ำเงิน (เปลี่ยนจาก #22a8e6)
            "accent_peas":   "#27ae60",   # 🟢 เขียว (คงเดิม)
            "accent_carrot": "#f58505",   # 🟠 ส้ม (คงเดิม)
            "accent_all":    "#8e44ad",
        }

        # โหลดโมเดลทั้งหมด
        self.models = {}
        self.load_all_models()

        # State
        self.current_image_path = None
        self.counts = {name: 0 for name in MODEL_CONFIGS}

        # UI
        self.setup_ui()

    # โหลดโมเดลทั้งหมด
    def load_all_models(self):
        failed = []
        for name, cfg in MODEL_CONFIGS.items():
            try:
                self.models[name] = YOLO(cfg["path"])
                print(f"[OK] Loaded: {name}")
            except Exception as e:
                print(f"[FAIL] {name}: {e}")
                failed.append(f"• {name}\n  Path: {cfg['path']}\n  Error: {e}")
        if failed:
            messagebox.showwarning("Model Load Warning", "\n\n".join(failed))
        if not self.models:
            messagebox.showerror("Fatal Error", "No models loaded.")
            self.root.destroy()

    # ─────────────── UI ───────────────
    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg=self.colors["bg_main"])
        main_frame.pack(fill="both", expand=True)

        sidebar = tk.Frame(main_frame, bg=self.colors["bg_sidebar"], width=370)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self._build_sidebar(sidebar)

        # ---- พื้นที่แสดงภาพ ----
        image_frame = tk.Frame(main_frame, bg=self.colors["bg_main"])
        image_frame.pack(side="right", fill="both", expand=True, padx=15, pady=15)

        self.canvas_frame = tk.Frame(image_frame, bg="#bdc3c7", bd=2, relief="sunken")
        self.canvas_frame.pack(fill="both", expand=True)

        self.lbl_image = tk.Label(
            self.canvas_frame,
            text="📂  Load an image to begin",
            font=("Segoe UI", 18),
            bg="#dfe6e9", fg="#7f8c8d"
        )
        self.lbl_image.pack(fill="both", expand=True)

        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief="sunken",
                                   anchor="w", font=("Segoe UI", 9), bg="#ecf0f1")
        self.status_bar.pack(side="bottom", fill="x")

    def _build_sidebar(self, sidebar):
        btn_frame = tk.Frame(sidebar, bg=self.colors["bg_sidebar"])
        btn_frame.pack(side="bottom", fill="x", padx=20, pady=15)

        self.btn_load = tk.Button(
            btn_frame, text="📂  LOAD & ANALYZE IMAGE",
            font=("Segoe UI", 13, "bold"),
            bg=self.colors["accent_peas"], fg="white",
            activebackground="#219150", activeforeground="white",
            relief="flat", cursor="hand2", height=2,
            command=self.load_image
        )
        self.btn_load.pack(fill="x")

        # Title
        tk.Label(sidebar, text="QC INSPECTION", font=("Segoe UI", 20, "bold"),
                 bg=self.colors["bg_sidebar"], fg=self.colors["text_light"]).pack(pady=(20, 2))
        tk.Label(sidebar, text="Triple AI Model System", font=("Segoe UI", 10),
                 bg=self.colors["bg_sidebar"], fg=self.colors["text_muted"]).pack(pady=(0, 8))
        ttk.Separator(sidebar, orient='horizontal').pack(fill='x', padx=20, pady=5)

        # Model Selector
        sel_frame = tk.LabelFrame(sidebar, text="  Model Selection  ",
                                  font=("Segoe UI", 10, "bold"),
                                  bg=self.colors["bg_sidebar"], fg=self.colors["text_light"],
                                  bd=1, relief="groove", padx=10, pady=6)
        sel_frame.pack(fill="x", padx=20, pady=8)

        self.model_var = tk.StringVar(value="All Models")
        options = list(MODEL_CONFIGS.keys()) + ["All Models"]
        for opt in options:
            rb = tk.Radiobutton(sel_frame, text=opt, variable=self.model_var, value=opt,
                                font=("Segoe UI", 10), bg=self.colors["bg_sidebar"],
                                fg=self.colors["text_light"],
                                selectcolor=self.colors["bg_panel"])
            rb.pack(anchor="w", pady=1)

        # Count cards
        count_frame = tk.Frame(sidebar, bg=self.colors["bg_sidebar"])
        count_frame.pack(fill="x", padx=20, pady=6)

        self._build_count_card(count_frame, "🥔 Potato", self.colors["accent_potato"], "lbl_potato").pack(
            side="left", expand=True, fill="x", padx=2)
        self._build_count_card(count_frame, "🫛 Peas", self.colors["accent_peas"], "lbl_peas").pack(
            side="left", expand=True, fill="x", padx=2)
        self._build_count_card(count_frame, "🥕 Carrot", self.colors["accent_carrot"], "lbl_carrot").pack(
            side="left", expand=True, fill="x", padx=2)

        total_frame = tk.Frame(sidebar, bg=self.colors["bg_panel"], pady=6)
        total_frame.pack(fill="x", padx=20, pady=(6, 8))
        tk.Label(total_frame, text="TOTAL COUNT", font=("Segoe UI", 9, "bold"),
                 bg=self.colors["bg_panel"], fg=self.colors["text_muted"]).pack()
        self.lbl_total = tk.Label(total_frame, text="0", font=("Segoe UI", 36, "bold"),
                                  bg=self.colors["bg_panel"], fg=self.colors["accent_all"])
        self.lbl_total.pack()

        # Confidence
        conf_frame = tk.LabelFrame(sidebar, text="  Detection Settings  ",
                                   font=("Segoe UI", 10, "bold"),
                                   bg=self.colors["bg_sidebar"], fg=self.colors["text_light"],
                                   bd=1, relief="groove", padx=10, pady=6)
        conf_frame.pack(fill="x", padx=20, pady=6)

        tk.Label(conf_frame, text="Confidence Threshold:",
                 bg=self.colors["bg_sidebar"], fg=self.colors["text_muted"]).pack(anchor="w")
        self.conf_slider = ttk.Scale(conf_frame, from_=0.1, to=1.0,
                                     orient='horizontal', command=self.update_conf_label)
        self.conf_slider.set(0.4)
        self.conf_slider.pack(fill="x", pady=4)
        self.lbl_conf_val = tk.Label(conf_frame, text="0.40", font=("Segoe UI", 9, "bold"),
                                     bg=self.colors["bg_sidebar"], fg=self.colors["accent_peas"])
        self.lbl_conf_val.pack(anchor="e")

    # การ์ดแสดงจำนวน
    def _build_count_card(self, parent, label, color, attr):
        frame = tk.Frame(parent, bg=self.colors["bg_panel"], pady=6)
        tk.Label(frame, text=label, font=("Segoe UI", 8, "bold"),
                 bg=self.colors["bg_panel"], fg=self.colors["text_muted"]).pack()
        lbl = tk.Label(frame, text="0", font=("Segoe UI", 30, "bold"),
                       bg=self.colors["bg_panel"], fg=color)
        lbl.pack()
        setattr(self, attr, lbl)
        return frame

    def update_conf_label(self, v):
        self.lbl_conf_val.config(text=f"{float(v):.2f}")

    # โหลดภาพ
    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg *.bmp")])
        if file_path:
            self.current_image_path = file_path
            self.status_bar.config(text="⏳ Processing...", fg="blue")
            self.btn_load.config(state="disabled")
            threading.Thread(target=self.process_image, daemon=True).start()

    # ประมวลผลภาพ
    def process_image(self):
        try:
            conf = self.conf_slider.get()
            selected = self.model_var.get()
            if selected == "All Models":
                self._run_all_models(conf)
            else:
                self._run_single_model(selected, conf)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.root.after(0, lambda: self.btn_load.config(state="normal"))

    # โมเดลเดียว
    def _run_single_model(self, model_name, conf):
        model = self.models[model_name]
        results = model.predict(source=self.current_image_path, conf=conf)
        result = results[0]
        count = len(result.boxes)
        img_array = cv2.cvtColor(result.plot(), cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_array)

        for name in MODEL_CONFIGS:
            if name == model_name:
                self.root.after(0, lambda n=name, c=count: self._update_count(n, c))
            else:
                self.root.after(0, lambda n=name: self._update_count(n, "–"))

        self.root.after(0, lambda: self._display_image(img_pil))
        self.root.after(0, lambda: self.status_bar.config(
            text=f"✅ {model_name} found {count} objects  (conf={conf:.2f})", fg="green"))

    # ทุกโมเดล
    def _run_all_models(self, conf):
        img_base = cv2.imread(self.current_image_path)
        image = img_base.copy()
        total = 0

        for name, model in self.models.items():
            results = model.predict(source=self.current_image_path, conf=conf)
            boxes = results[0].boxes
            count = len(boxes)
            total += count
            color = tuple(int(MODEL_CONFIGS[name]["color"].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf_val = float(box.conf[0])
                cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                cv2.putText(image, f"{name.split()[0]} {conf_val:.2f}", (x1, max(y1-6, 12)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            self.root.after(0, lambda n=name, c=count: self._update_count(n, c))

        img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        self.root.after(0, lambda: self._display_image(img_pil))
        self.root.after(0, lambda: self.lbl_total.config(text=str(total)))
        self.root.after(0, lambda: self.status_bar.config(
            text=f"✅ ALL MODELS DONE | Total: {total} (conf={conf:.2f})", fg="purple"))

    def _update_count(self, model_name, count):
        lbl_map = {
            "Potato Model": self.lbl_potato,
            "Peas Model": self.lbl_peas,
            "Carrot Model": self.lbl_carrot,
        }
        lbl = lbl_map.get(model_name)
        if lbl:
            lbl.config(text=str(count))

    def _display_image(self, img_pil):
        img_pil = self._resize_to_fit(img_pil, self.canvas_frame.winfo_width(),
                                      self.canvas_frame.winfo_height())
        img_tk = ImageTk.PhotoImage(img_pil)
        self.lbl_image.config(image=img_tk, text="")
        self.lbl_image.image = img_tk

    def _resize_to_fit(self, img, max_w, max_h):
        w, h = img.size
        ratio = min(max_w / w, max_h / h)
        if ratio >= 1:
            return img
        return img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)


if __name__ == "__main__":
    root = tk.Tk()
    app = QCInspectionApp(root)
    root.mainloop()