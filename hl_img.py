#!/usr/bin/env python3
"""
Half-Life PS2 DOL Texture Viewer
--------------------------------------------------------
• Texture always scales to fit the canvas/window
• Dark theme UI
• PS2 palette reformat
• Save 8-bit PNG
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import struct

HEADER_FIELDS = [
    ("id", 0), ("version", 4), ("name", 8), ("length", 72),
    ("eyeposition", 76), ("min", 88), ("max", 100),
    ("bbmin", 112), ("bbmax", 124), ("flags", 136),
    ("numbones", 140), ("boneindex", 144),
    ("numbonecontrollers", 148), ("bonecontrollerindex", 152),
    ("numhitboxes", 156), ("hitboxindex", 160),
    ("numseq", 164), ("seqindex", 168),
    ("numseqgroups", 172), ("seqgroupindex", 176),
    ("numtextures", 180), ("textureindex", 184),
    ("texturedataindex", 188), ("numskinref", 192),
    ("numskinfamilies", 196), ("skinindex", 200),
    ("numbodyparts", 204), ("bodypartindex", 208),
    ("numattachments", 212), ("attachmentindex", 216),
    ("soundtable", 220), ("soundindex", 224),
    ("soundgroups", 228), ("soundgroupindex", 232),
    ("numtransitions", 236), ("transitionindex", 240)
]

TEXTURE_FIELDS = [
    ("tex_name", 0), ("tex_flags", 64),
    ("tex_width", 68), ("tex_height", 72),
    ("tex_index", 76)
]

class MDLViewerDarkFit:
    def __init__(self, root):
        self.root = root
        self.root.title("Half-Life MDL Texture Viewer")
        self.data = None
        self.textures = []
        self.current_tex = 0
        self.entries = {}
        self.tex_entries = {}
        self.img_cache = None  # store resized PIL image

        # Dark theme colors
        self.bg_color = "#2b2b2b"
        self.fg_color = "#f0f0f0"
        self.entry_bg = "#3c3f41"
        self.entry_fg = "#f0f0f0"
        root.configure(bg=self.bg_color)

        # Menu
        menu = tk.Menu(root, bg=self.bg_color, fg=self.fg_color)
        root.config(menu=menu)
        file_menu = tk.Menu(menu, tearoff=0, bg=self.bg_color, fg=self.fg_color)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open .DOL File", command=self.load_mdl)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)

        # Header frame
        header_frame = tk.LabelFrame(root, text="DOL Header", padx=5, pady=5,
                                     bg=self.bg_color, fg=self.fg_color)
        header_frame.pack(padx=10, pady=5, fill="x")
        for i, (name, _) in enumerate(HEADER_FIELDS):
            label = tk.Label(header_frame, text=name, anchor="e", bg=self.bg_color, fg=self.fg_color)
            label.grid(row=i // 4, column=(i % 4) * 2, sticky="e")
            entry = tk.Entry(header_frame, width=12, bg=self.entry_bg, fg=self.entry_fg,
                             insertbackground=self.fg_color)
            entry.grid(row=i // 4, column=(i % 4) * 2 + 1)
            self.entries[name] = entry

        # Texture header frame
        tex_frame = tk.LabelFrame(root, text="Texture Header", padx=5, pady=5,
                                  bg=self.bg_color, fg=self.fg_color)
        tex_frame.pack(padx=10, pady=5, fill="x")
        for i, (name, _) in enumerate(TEXTURE_FIELDS):
            label = tk.Label(tex_frame, text=name, bg=self.bg_color, fg=self.fg_color)
            label.grid(row=0, column=i * 2, sticky="e")
            entry = tk.Entry(tex_frame, width=20, bg=self.entry_bg, fg=self.entry_fg,
                             insertbackground=self.fg_color)
            entry.grid(row=0, column=i * 2 + 1)
            self.tex_entries[name] = entry

        # Texture list
        self.tex_list = tk.Listbox(root, width=50, height=6, bg=self.entry_bg, fg=self.fg_color,
                                   selectbackground="#4b6eaf", selectforeground="#ffffff")
        self.tex_list.pack(pady=5)
        self.tex_list.bind("<<ListboxSelect>>", self.on_tex_select)

        # Buttons
        btn_frame = tk.Frame(root, bg=self.bg_color)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="💾 Save Selected 8-bit PNG", command=self.save_selected_png8,
                  bg=self.entry_bg, fg=self.fg_color).pack(side="left", padx=5)
        tk.Button(btn_frame, text="📁 Save All 8-bit PNGs", command=self.save_all_png8,
                  bg=self.entry_bg, fg=self.fg_color).pack(side="left", padx=5)

        # Canvas
        self.canvas = tk.Canvas(root, bg="black")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.render_texture())  # re-render on resize

        # Palette Reformat
        self.reformat_var = tk.BooleanVar(value=True)

    # ---------------------------
    # Load MDL
    # ---------------------------
    def load_mdl(self):
        filepath = filedialog.askopenfilename(filetypes=[("StudioModel PS2 files", "*.dol")])
        if not filepath:
            return
        try:
            with open(filepath, "rb") as f:
                self.data = f.read()

            # Parse header fields
            for name, offset in HEADER_FIELDS:
                if name == "name":
                    value = self.data[offset:offset + 64].split(b"\x00")[0].decode(errors="ignore")
                elif name in ["eyeposition", "min", "max", "bbmin", "bbmax"]:
                    value = struct.unpack_from("<3f", self.data, offset)
                    value = f"{value[0]:.2f},{value[1]:.2f},{value[2]:.2f}"
                else:
                    value = struct.unpack_from("<I", self.data, offset)[0]
                self.entries[name].delete(0, tk.END)
                self.entries[name].insert(0, str(value))

            textureindex = int(self.entries["textureindex"].get())
            texturedataindex = int(self.entries["texturedataindex"].get())
            numtextures = int(self.entries["numtextures"].get())
            self.textures = []

            data_offset = texturedataindex + 32
            for i in range(numtextures):
                base = textureindex + i * 80
                tex_name = self.data[base:base + 64].split(b"\x00")[0].decode(errors="ignore")
                tex_flags = struct.unpack_from("<I", self.data, base + 64)[0]
                tex_width = struct.unpack_from("<I", self.data, base + 68)[0]
                tex_height = struct.unpack_from("<I", self.data, base + 72)[0]

                palette_raw = self.data[data_offset:data_offset + 1024]
                if self.reformat_var.get():
                    palette_raw = self.ps2_palette_reformat(palette_raw)

                self.textures.append({
                    "name": tex_name,
                    "flags": tex_flags,
                    "width": tex_width,
                    "height": tex_height,
                    "offset": data_offset,
                    "palette": palette_raw
                })
                data_offset += 1024 + 32 + (tex_width * tex_height)

            # Populate listbox
            self.tex_list.delete(0, tk.END)
            for i, t in enumerate(self.textures):
                self.tex_list.insert(tk.END, f"{i}: {t['name']}")
            self.tex_list.select_set(0)
            self.on_tex_select(None)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------------------------
    # Palette Reformat
    # ---------------------------
    def ps2_palette_reformat(self, pal, s=4):
        p = bytearray(pal)
        for i in range(len(p)):
            r = i % (0x20 * s)
            if 0x10 * s <= r < 0x18 * s:
                p[i], p[i - 0x08 * s] = p[i - 0x08 * s], p[i]
        return bytes(p)

    # ---------------------------
    # Render Texture
    # ---------------------------
    def render_texture(self):
        if not self.textures or self.data is None:
            return
        tex = self.textures[self.current_tex]
        img = self.get_texture_image(tex)
        if img is None:
            return

        # Auto-fit canvas
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        img_ratio = tex["width"] / tex["height"]
        canvas_ratio = canvas_w / canvas_h

        if img_ratio > canvas_ratio:
            new_w = canvas_w
            new_h = int(canvas_w / img_ratio)
        else:
            new_h = canvas_h
            new_w = int(canvas_h * img_ratio)

        img_resized = img.resize((new_w, new_h), Image.NEAREST)
        tk_img = ImageTk.PhotoImage(img_resized)
        self.canvas.delete("all")
        self.canvas.create_image(canvas_w // 2, canvas_h // 2, anchor="center", image=tk_img)
        self.canvas.image = tk_img
        self.img_cache = tk_img

        # Update texture info fields
        for key, entry in self.tex_entries.items():
            entry.delete(0, tk.END)
        self.tex_entries["tex_name"].insert(0, tex["name"])
        self.tex_entries["tex_flags"].insert(0, tex["flags"])
        self.tex_entries["tex_width"].insert(0, tex["width"])
        self.tex_entries["tex_height"].insert(0, tex["height"])
        self.tex_entries["tex_index"].insert(0, f"{tex['offset']:#x}")

    # ---------------------------
    # Convert to PIL Image
    # ---------------------------
    def get_texture_image(self, tex):
        try:
            palette_raw = tex["palette"]
            width, height = tex["width"], tex["height"]
            offset = tex["offset"]
            palette = [tuple(palette_raw[i:i + 3]) for i in range(0, 1024, 4)]
            pixel_data = self.data[offset + 1024:offset + 1024 + width * height]
            pixels = [palette[i % len(palette)] for i in pixel_data]
            img = Image.new("RGB", (width, height))
            img.putdata(pixels)
            return img
        except Exception:
            return None

    # ---------------------------
    # Texture selection
    # ---------------------------
    def on_tex_select(self, event):
        sel = self.tex_list.curselection()
        if sel:
            self.current_tex = sel[0]
            self.render_texture()

    # ---------------------------
    # Save 8-bit PNG
    # ---------------------------
    def save_selected_png8(self):
        tex = self.textures[self.current_tex]
        img = self.get_texture_image(tex)
        if img is None:
            return
        img8 = img.convert("P", palette=Image.ADAPTIVE, colors=256)
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("8-bit PNG", "*.png")],
                                                 initialfile=f"{tex['name'].lower().replace('.bmp', '')}.png")
        if not file_path:
            return
        try:
            img8.save(file_path, "PNG")
            messagebox.showinfo("Saved", f"Saved {os.path.basename(file_path)} as 8-bit PNG")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save PNG:\n{e}")

    def save_all_png8(self):
        folder = filedialog.askdirectory(title="Select Folder to Save 8-bit PNGs")
        if not folder:
            return
        count = 0
        for tex in self.textures:
            img = self.get_texture_image(tex)
            if img:
                img8 = img.convert("P", palette=Image.ADAPTIVE, colors=256)
                safe_name = tex['name'] or f"texture_{count}"
                file_path = os.path.join(folder, f"{safe_name.lower().replace('.bmp', '')}.png")
                img8.save(file_path, "PNG")
                count += 1
        messagebox.showinfo("Saved", f"Saved {count} textures as 8-bit PNGs to:\n{folder}")


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("800x600")
    app = MDLViewerDarkFit(root)
    root.mainloop()
