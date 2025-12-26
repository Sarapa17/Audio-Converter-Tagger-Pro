import sys
import subprocess
import os
import shutil
import threading
import io
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TCON, TYER, TRCK
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image
import numpy as np
from scipy.fft import fft

TAG_CONFIG = {
    "Song Name":    {"mp3": "title",       "m4a": "\xa9nam", "flac": "title"},
    "Artist":       {"mp3": "artist",      "m4a": "\xa9ART", "flac": "artist"},
    "Album":        {"mp3": "album",       "m4a": "\xa9alb", "flac": "album"},
    "Genre":        {"mp3": "genre",       "m4a": "\xa9gen", "flac": "genre"},
    "Year":         {"mp3": "date",        "m4a": "\xa9day", "flac": "date"},
    "Track Number": {"mp3": "tracknumber", "m4a": "trkn",    "flac": "tracknumber"}
}

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AudioApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)
        self.title("Audio Converter & Tagger Pro (Optimized)")
        self.geometry("1150x850") 

        self.ffmpeg_path = self.find_ffmpeg()
        if self.ffmpeg_path is None:
            messagebox.showerror("Falta FFmpeg", "No se encontró 'ffmpeg'.")
        
        self.files_data = [] 
        self.current_selection_index = None
        self.output_folder = os.path.join(os.path.expanduser("~"), "Downloads")
        
        self.grid_columnconfigure(0, weight=4) 
        self.grid_columnconfigure(1, weight=6) 
        self.grid_rowconfigure(0, weight=1)

        self.setup_ui()

    def find_ffmpeg(self):
        path = shutil.which("ffmpeg")
        if path: return path
        local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg")
        return local if os.path.exists(local) else None

    def setup_ui(self):
        self.frame_editor = ctk.CTkFrame(self, corner_radius=0)
        self.frame_editor.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        
        ctk.CTkLabel(self.frame_editor, text="DETALLES Y ETIQUETAS", font=("Roboto", 18, "bold")).pack(pady=10)
        self.frame_editor.drop_target_register(DND_FILES)
        self.frame_editor.dnd_bind('<<Drop>>', self.drop_on_editor)

        self.lbl_quality_info = ctk.CTkLabel(self.frame_editor, text="HEADER: ---", font=("Roboto", 13), text_color="gray")
        self.lbl_quality_info.pack(pady=2)

        self.lbl_real_quality = ctk.CTkLabel(self.frame_editor, text="CALIDAD REAL: Pendiente", font=("Roboto", 14, "bold"), text_color="#38bdf8")
        self.lbl_real_quality.pack(pady=5)

        self.btn_verify_real = ctk.CTkButton(self.frame_editor, text="🔍 VERIFICAR INTEGRIDAD (FFT)", 
                                             command=self.start_verify_thread, fg_color="#1e293b")
        self.btn_verify_real.pack(pady=5)

        frame_fn = ctk.CTkFrame(self.frame_editor, fg_color="transparent")
        frame_fn.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(frame_fn, text="ARCHIVO:", width=100, anchor="w").pack(side="left")
        self.entry_filename = ctk.CTkEntry(frame_fn, height=28)
        self.entry_filename.pack(side="left", fill="x", expand=True)

        self.entries = {}
        for field in TAG_CONFIG.keys():
            frame = ctk.CTkFrame(self.frame_editor, fg_color="transparent")
            frame.pack(fill="x", padx=20, pady=2)
            ctk.CTkLabel(frame, text=field.upper() + ":", width=100, anchor="w", font=("Roboto", 11)).pack(side="left")
            entry = ctk.CTkEntry(frame, height=28)
            entry.pack(side="left", fill="x", expand=True)
            self.entries[field] = entry

        self.lbl_cover_preview = ctk.CTkLabel(self.frame_editor, text="[Sin Vista Previa]", width=160, height=160, fg_color="#333", corner_radius=5)
        self.lbl_cover_preview.pack(pady=15)

        btn_img_frame = ctk.CTkFrame(self.frame_editor, fg_color="transparent")
        btn_img_frame.pack(fill="x", padx=20)
        ctk.CTkButton(btn_img_frame, text="Imagen", command=self.browse_cover_art, height=30, fg_color="#444").pack(side="left", fill="x", expand=True, padx=2)
        self.btn_delete_cover = ctk.CTkButton(btn_img_frame, text="X", command=self.delete_current_cover, width=40, height=30, fg_color="#c42b1c")
        self.btn_delete_cover.pack(side="right", padx=2)

        ctk.CTkButton(self.frame_editor, text="GUARDAR CAMBIOS", command=self.save_tags, height=50, font=("Roboto", 14, "bold")).pack(pady=20, padx=20, fill="x", side="bottom")

        self.frame_converter = ctk.CTkFrame(self, corner_radius=0)
        self.frame_converter.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        self.scroll_frame = ctk.CTkScrollableFrame(self.frame_converter, label_text="Cola de Procesamiento")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.scroll_frame.drop_target_register(DND_FILES)
        self.scroll_frame.dnd_bind('<<Drop>>', self.drop_on_converter)

        controls = ctk.CTkFrame(self.frame_converter, fg_color="transparent")
        controls.pack(fill="x", padx=20, pady=20)
        self.lbl_output = ctk.CTkLabel(controls, text=f"Destino: {os.path.basename(self.output_folder)}")
        self.lbl_output.pack(side="left", padx=5)
        ctk.CTkButton(controls, text="Carpeta", width=80, command=self.change_output_folder).pack(side="left", padx=5)
        self.btn_convert = ctk.CTkButton(controls, text="PROCESAR TODO", fg_color="#1f6aa5", command=self.start_conversion_thread)
        self.btn_convert.pack(side="right", padx=5)

    def start_verify_thread(self):
        if self.current_selection_index is None: return
        self.btn_verify_real.configure(state="disabled", text="Analizando...")
        threading.Thread(target=self.perform_spectral_analysis, daemon=True).start()

    def perform_spectral_analysis(self):
        obj = self.files_data[self.current_selection_index]
        try:
            cmd = [self.ffmpeg_path, "-ss", "30", "-t", "5", "-i", obj['path'], "-f", "s16le", "-ac", "1", "-ar", "44100", "-"]
            
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
                raw_audio = process.stdout.read()

            if not raw_audio:
                result, color = "Error de lectura", "red"
            else:
                audio_data = np.frombuffer(raw_audio, dtype=np.int16)
                yf = fft(audio_data)
                xf = np.linspace(0.0, 44100 // 2, len(audio_data) // 2)
                mag = 20 * np.log10(np.abs(yf[:len(audio_data) // 2]) + 1e-6)
                indices = np.where(mag > -60)[0]
                
                if len(indices) == 0:
                    result, color = "Silencio", "red"
                else:
                    cutoff = xf[indices[-1]] / 1000 
                    if cutoff >= 18.5: result, color = f"REAL 320kbps ({cutoff:.1f} kHz)", "#4ade80"
                    elif cutoff >= 16.0: result, color = f"REAL ~256kbps ({cutoff:.1f} kHz)", "#facc15"
                    elif cutoff >= 13.5: result, color = f"FAKE 320 (Real 128k) ({cutoff:.1f} kHz)", "#f87171"
                    else: result, color = f"BAJA ({cutoff:.1f} kHz)", "#ef4444"

            self.after(0, lambda: self.update_quality_ui(result, color))
        except Exception as e:
            self.after(0, lambda: self.update_quality_ui(f"Error", "red"))

    def update_quality_ui(self, text, color):
        self.lbl_real_quality.configure(text=f"CALIDAD REAL: {text}", text_color=color)
        self.btn_verify_real.configure(state="normal", text="🔍 VERIFICAR INTEGRIDAD (FFT)")

    def read_metadata_from_file(self, file_obj):
        try:
            path, ext = file_obj['path'], file_obj['ext'].replace('.','')
            tags, cover_data, quality = {}, None, "Desconocido"

            if ext == 'mp3':
                audio = MP3(path)
                quality = f"{int(audio.info.bitrate/1000)} kbps / {audio.info.sample_rate/1000} kHz"
                ez = EasyID3(path)
                for label, keys in TAG_CONFIG.items():
                    tags[label] = ez.get(keys['mp3'], [''])[0]
                if audio.tags:
                    for tag in audio.tags.values():
                        if isinstance(tag, APIC): cover_data = tag.data; break
            
            elif ext == 'm4a':
                audio = MP4(path)
                quality = f"{int(audio.info.bitrate/1000)} kbps / {audio.info.sample_rate/1000} kHz"
                for label, keys in TAG_CONFIG.items():
                    val = audio.get(keys['m4a'], [''])
                    tags[label] = str(val[0][0]) if label == "Track Number" and val != [''] else str(val[0])
                if 'covr' in audio: cover_data = audio['covr'][0]

            elif ext == 'flac':
                audio = FLAC(path)
                quality = f"LOSSLESS {audio.info.bits_per_sample}bit / {audio.info.sample_rate/1000} kHz"
                for label, keys in TAG_CONFIG.items():
                    tags[label] = audio.get(keys['flac'], [''])[0]
                if audio.pictures: cover_data = audio.pictures[0].data

            file_obj.update({'tags': tags, 'cover_bytes': cover_data, 'quality': quality})
        except: pass

    def update_cover_preview(self, file_obj):
        if file_obj.get('ctk_thumb') and not file_obj.get('new_cover_path') and not file_obj.get('delete_cover'):
            self.lbl_cover_preview.configure(image=file_obj['ctk_thumb'], text="")
            self.btn_delete_cover.configure(state="normal")
            return

        image_data = None
        if file_obj.get('new_cover_path'):
            with open(file_obj['new_cover_path'], 'rb') as f: image_data = f.read()
        elif file_obj.get('cover_bytes') and not file_obj.get('delete_cover'):
            image_data = file_obj['cover_bytes']

        if image_data:
            try:
                img = Image.open(io.BytesIO(image_data))
                img.thumbnail((160, 160))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 160))
                file_obj['ctk_thumb'] = ctk_img # Guardar en cache
                self.lbl_cover_preview.configure(image=ctk_img, text="")
                self.btn_delete_cover.configure(state="normal")
            except: self.lbl_cover_preview.configure(image=None, text="Error")
        else:
            self.lbl_cover_preview.configure(image=None, text="Sin Carátula")
            self.btn_delete_cover.configure(state="disabled")

    def save_tags(self):
        if self.current_selection_index is None: return
        obj = self.files_data[self.current_selection_index]
        for key, entry in self.entries.items(): obj['tags'][key] = entry.get()
        
        if obj['ext'] == '.mp3': self.apply_tags_to_mp3(obj)
        elif obj['ext'] == '.m4a': self.apply_tags_to_m4a(obj)
        
        obj['lbl_status'].configure(text="Saved", text_color="green")
        messagebox.showinfo("OK", "Guardado.")

    def apply_tags_to_mp3(self, obj):
        try:
            audio = MP3(obj['path'], ID3=ID3)
            try: audio.add_tags()
            except: pass
            t = obj['tags']
            audio.tags.add(TIT2(encoding=3, text=t.get("Song Name","")))
            audio.tags.add(TPE1(encoding=3, text=t.get("Artist","")))
            audio.tags.add(TALB(encoding=3, text=t.get("Album","")))
            audio.tags.add(TCON(encoding=3, text=t.get("Genre","")))
            audio.tags.add(TYER(encoding=3, text=str(t.get("Year",""))))
            audio.tags.add(TRCK(encoding=3, text=str(t.get("Track Number",""))))
            audio.tags.delall("APIC")
            
            final_img = None
            if obj.get('new_cover_path'):
                with open(obj['new_cover_path'], 'rb') as f: final_img = f.read()
            elif obj.get('cover_bytes') and not obj.get('delete_cover'): final_img = obj['cover_bytes']
            
            if final_img: audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=final_img))
            audio.save()
            obj.update({'cover_bytes': final_img, 'new_cover_path': None, 'delete_cover': False, 'ctk_thumb': None})
        except: pass

    def apply_tags_to_m4a(self, obj):
        try:
            audio = MP4(obj['path'])
            t = obj['tags']
            audio['\xa9nam'], audio['\xa9ART'], audio['\xa9alb'] = t.get("Song Name",""), t.get("Artist",""), t.get("Album","")
            audio['\xa9gen'], audio['\xa9day'] = t.get("Genre",""), t.get("Year","")
            try: audio['trkn'] = [(int(t.get("Track Number",0)), 0)]
            except: pass
            
            final_img = None
            if obj.get('new_cover_path'):
                with open(obj['new_cover_path'], 'rb') as f: final_img = f.read()
            elif obj.get('cover_bytes') and not obj.get('delete_cover'): final_img = obj['cover_bytes']
            
            if final_img:
                fmt = MP4Cover.FORMAT_PNG if Image.open(io.BytesIO(final_img)).format == 'PNG' else MP4Cover.FORMAT_JPEG
                audio['covr'] = [MP4Cover(final_img, imageformat=fmt)]
            elif obj.get('delete_cover'): audio.pop('covr', None)
            audio.save()
            obj.update({'cover_bytes': final_img, 'new_cover_path': None, 'delete_cover': False, 'ctk_thumb': None})
        except: pass

    def start_conversion_thread(self):
        threading.Thread(target=self.process_queue, daemon=True).start()

    def process_queue(self):
        self.btn_convert.configure(state="disabled")
        for obj in self.files_data:
            if obj['ext'] in ['.wav', '.flac']:
                obj['lbl_status'].configure(text="Converting...", text_color="yellow")
                out_p = os.path.join(self.output_folder, os.path.splitext(obj['filename'])[0] + ".mp3")
                try:
                    subprocess.run([self.ffmpeg_path, "-y", "-i", obj['path'], "-b:a", "320k", "-threads", "0", "-id3v2_version", "3", out_p], check=True, capture_output=True)
                    temp = obj.copy(); temp['path'] = out_p
                    self.apply_tags_to_mp3(temp)
                    obj['lbl_status'].configure(text="Done", text_color="green")
                    obj['progress_bar'].set(1)
                except: obj['lbl_status'].configure(text="Error", text_color="red")
            else:
                obj['lbl_status'].configure(text="Done", text_color="green")
                obj['progress_bar'].set(1)
        self.btn_convert.configure(state="normal")
        messagebox.showinfo("Fin", "Proceso terminado.")

    def register_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext not in ['.flac', '.wav', '.mp3', '.m4a']: return -1
        for idx, f_data in enumerate(self.files_data):
            if f_data['path'] == path: return idx
        file_obj = {"path": path, "filename": os.path.basename(path), "ext": ext, "status": "Ready", "tags": {}, "widget": None, "lbl_status": None, "progress_bar": None, "cover_bytes": None, "new_cover_path": None, "delete_cover": False, "ctk_thumb": None}
        self.files_data.append(file_obj)
        self.add_file_to_ui(file_obj)
        self.read_metadata_from_file(file_obj)
        return len(self.files_data) - 1

    def add_file_to_ui(self, file_obj):
        row = ctk.CTkFrame(self.scroll_frame)
        row.pack(fill="x", pady=2)
        lbl_name = ctk.CTkLabel(row, text=file_obj['filename'], width=220, anchor="w")
        lbl_name.pack(side="left", padx=10)
        lbl_status = ctk.CTkLabel(row, text=file_obj['status'], width=100, text_color="orange")
        lbl_status.pack(side="right", padx=10)
        progress = ctk.CTkProgressBar(row, width=80); progress.set(0); progress.pack(side="right", padx=10)
        file_obj.update({'widget': row, 'lbl_name': lbl_name, 'lbl_status': lbl_status, 'progress_bar': progress})
        row.bind("<Button-1>", lambda e, obj=file_obj: self.manual_select(obj))

    def manual_select(self, file_obj):
        idx = self.files_data.index(file_obj)
        self.load_to_editor(idx)

    def drop_on_converter(self, event):
        for f in self.tk.splitlist(event.data): self.register_file(f)

    def drop_on_editor(self, event):
        idx = -1
        for f in self.tk.splitlist(event.data): idx = self.register_file(f)
        if idx != -1: self.load_to_editor(idx)

    def browse_cover_art(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if path and self.current_selection_index is not None:
            obj = self.files_data[self.current_selection_index]
            obj['new_cover_path'], obj['delete_cover'] = path, False
            self.update_cover_preview(obj)

    def delete_current_cover(self):
        if self.current_selection_index is not None:
            obj = self.files_data[self.current_selection_index]
            obj['delete_cover'], obj['new_cover_path'] = True, None
            self.update_cover_preview(obj)

    def change_output_folder(self):
        folder = filedialog.askdirectory()
        if folder: self.output_folder = folder; self.lbl_output.configure(text=f"Destino: {os.path.basename(folder)}")

if __name__ == "__main__":
    app = AudioApp()
    app.mainloop()