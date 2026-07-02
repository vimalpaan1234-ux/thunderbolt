import os
import requests
import threading
import concurrent.futures
import customtkinter as ctk
from tkinter import filedialog

# Initialize UI Theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class SpeedDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("ThunderBolt Downloader")
        self.geometry("600x350")
        self.resizable(False, False)

        # UI Elements
        self.label = ctk.CTkLabel(self, text="⚡ Multi-Threaded Speed Downloader", font=("Arial", 20, "bold"))
        self.label.pack(pady=20)

        self.url_input = ctk.CTkEntry(self, placeholder_text="Paste your download URL here...", width=500)
        self.url_input.pack(pady=10)

        self.threads_input = ctk.CTkComboBox(self, values=["4", "8", "16", "32"], width=120)
        self.threads_input.set("8")  # Default threads
        self.threads_input.pack(pady=5)

        self.status_label = ctk.CTkLabel(self, text="Status: Idle", font=("Arial", 12))
        self.status_label.pack(pady=10)

        self.download_btn = ctk.CTkButton(self, text="Start High-Speed Download", command=self.start_download_thread, fg_color="#1f6aa5", font=("Arial", 14, "bold"))
        self.download_btn.pack(pady=20)

    def download_chunk(self, url, start, end, chunk_idx, base_filename):
        chunk_filename = f"{base_filename}.part{chunk_idx}"
        downloaded_bytes = 0

        # Unbreakable Logic: Resume chunk if it already partially exists
        if os.path.exists(chunk_filename):
            downloaded_bytes = os.path.getsize(chunk_filename)
            if downloaded_bytes >= (end - start + 1):
                return

        resume_start = start + downloaded_bytes
        headers = {"Range": f"bytes={resume_start}-{end}"}
        
        try:
            response = requests.get(url, headers=headers, stream=True, timeout=15)
            with open(chunk_filename, "ab") as f:
                for data in response.iter_content(chunk_size=1024*64): # 64KB pieces
                    if data:
                        f.write(data)
        except Exception as e:
            print(f"Connection dropped on thread {chunk_idx}. Retrying is handled on next run.")

    def merge_chunks(self, final_path, num_threads):
        self.update_status("Assembling file fragments...")
        with open(final_path, "wb") as outfile:
            for i in range(num_threads):
                chunk_filename = f"{final_path}.part{i}"
                if os.path.exists(chunk_filename):
                    with open(chunk_filename, "rb") as infile:
                        outfile.write(infile.read())
                    os.remove(chunk_filename)
        self.update_status("Download Complete! 🎉")
        self.download_btn.configure(state="normal")

    def core_download_engine(self, url, final_path, num_threads):
        try:
            response = requests.head(url, timeout=10)
            file_size = int(response.headers.get("Content-Length", 0))
            
            if file_size == 0:
                self.update_status("Error: Server refused connection or invalid file.")
                self.download_btn.configure(state="normal")
                return

            chunk_size = file_size // num_threads
            futures = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                for i in range(num_threads):
                    start = i * chunk_size
                    end = file_size - 1 if i == num_threads - 1 else (start + chunk_size - 1)
                    futures.append(executor.submit(self.download_chunk, url, start, end, i, final_path))
                    
            concurrent.futures.wait(futures)
            self.merge_chunks(final_path, num_threads)
            
        except Exception as e:
            self.update_status(f"Error: Connection lost. Click download again to resume.")
            self.download_btn.configure(state="normal")

    def start_download_thread(self):
        url = self.url_input.get().strip()
        if not url:
            self.update_status("Please enter a valid URL.")
            return

        # Prompt user where to save the file
        suggested_name = url.split("/")[-1].split("?")[0] or "downloaded_file"
        save_path = filedialog.asksaveasfilename(initialfile=suggested_name)
        
        if not save_path:
            return

        num_threads = int(self.threads_input.get())
        self.update_status(f"Downloading via {num_threads} parallel streams...")
        self.download_btn.configure(state="disabled")

        # Run engine in background so the UI windows stays responsive
        downloader_thread = threading.Thread(target=self.core_download_engine, args=(url, save_path, num_threads))
        downloader_thread.start()

    def update_status(self, text):
        self.status_label.configure(text=f"Status: {text}")

if __name__ == "__main__":
    app = SpeedDownloaderApp()
    app.mainloop()