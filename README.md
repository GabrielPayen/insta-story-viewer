
# 📱 Insta Story Archive Viewer

## For how long would Insta last ? No one knows. 

**For those how like to archive media, here is a little tool for rendering the dump providing by Insta.**

A lightweight, self-hosted web gallery designed to browse your Instagram story archives. It automatically organizes media by year and month, provides a cinematic horizontal timeline.


## 🚀 Quick Start


### 0. How to get your Instagram Data

To use this viewer, you need a "JSON" format export from Instagram. Follow these steps:

1.  **Go to Accounts Center:** Open Instagram on your computer or phone and navigate to **Settings** > **Accounts Center** > **Your information and permissions**.
2.  **Download Your Information:** Click on **Download your information** and then **Request a download**.
3.  **Select Account:** Choose your Instagram profile.
4.  **Select Types of Information:** * Choose **"Specific types of information"** (this is faster than a complete copy).
    * Select **Content** (this includes your Stories).
5.  **Select Destination:** Choose **Download to device**.
6.  **Crucial Settings:**
    * **Date Range:** Select "All time" (or your preferred range).
    * **Format:** Select **JSON** (The viewer is optimized for this folder structure).
    * **Media Quality:** Select **High**.
7.  **Submit:** Click **Create files**. 

**Note:** It usually takes Instagram anywhere from 30 minutes to 48 hours to prepare the file. Once ready, they will email you a link to download a `.zip` file. Unzip that file and point this viewer to the resulting folder!

### 1. Install Dependencies
You will need Python 3.8+ and a few libraries for image processing and environment management:

```bash
pip install pillow pillow-heif python-dotenv
```

### 2. Run the Viewer
Navigate to the directory containing `viewer.py` and start the server:

```bash
python viewer.py
```

### 3. Initialize Setup
1.  Click the link generated in your terminal (usually `http://localhost:8000/media/archives/insta/archives`).
2.  Use the **Archive Setup** interface to navigate to your archive folder.
3.  Ensure you are inside the folder that contains the `stories/` directory.
4.  Click **Select This Folder**.

---

## 📂 Expected Folder Structure
The viewer is optimized for the standard Instagram "Download Your Information" export format:

```text
Your_Archive_Folder/    
└── stories/
    ├── 202301/           # Folder for Jan 2023
    │   ├── image_01.jpg
    │   └── video_02.mp4
    ├── 202302/           # Folder for Feb 2023
    └── ...
```

---

## 🛠️ Configuration
The script manages settings via a `.env` file in the project root. You can manually edit these if needed:

| Key | Description |
| :--- | :--- |
| `ARCHIVE_PATH` | The absolute path to the folder containing your `stories` directory. |
| `PORT` | The network port. Set to `0` to let the script find any available port. |

---

## ⌨️ Controls
* **Navigation:** Use your mouse wheel to scroll vertically within years, or **Shift + Scroll** to move horizontally through the timeline.
* **View Media:** Click any item to open the Lightbox.
* **Close Lightbox:** Click anywhere on the dark background to return to the timeline.
* **Exit Server:** Press `Ctrl+C` in your terminal. The script is configured to release the network port immediately upon exit.

---

### 📝 Note on First-Run Conversion
If your archive contains `.heic` files (common for iPhone users), the terminal will display "Pre-converting" the first time you load a specific folder. The script creates a `.jpg` copy next to the original to ensure it can be displayed in all web browsers. This only happens once.

Author: Gabriel Payen