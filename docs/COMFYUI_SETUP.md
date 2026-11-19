# MYRA local image engine (Windows)

MYRA's Telegram and desktop image-generation routes use ComfyUI on loopback only. No hosted image API, account token, or per-image service is required.

## Hardware profile

The current workstation has an NVIDIA RTX A2000 Laptop GPU with 4 GB VRAM. Use the NVIDIA portable ComfyUI package with low-VRAM offloading and CPU VAE. Keep initial generations at 512×512 and 20–25 steps; larger resolutions can run out of memory or become very slow.

## Install ComfyUI

1. Download the official [ComfyUI Windows portable NVIDIA package](https://github.com/Comfy-Org/ComfyUI/releases/download/v0.46.0/ComfyUI_windows_portable_nvidia.7z). The verified v0.46.0 archive SHA-256 is `6a5255c7ec01fdc54bdbd8e4507073cf6acda2fbeea74ae1829a50681af5fac6`.
2. Extract the archive into `%LOCALAPPDATA%\MYRA\ComfyUI` so that the folder contains `python_embeded\python.exe` and `ComfyUI\main.py`.
3. Install a compatible SD 1.5 checkpoint into `ComfyUI\models\checkpoints`. The current candidate is [DreamShaper 8](https://huggingface.co/Lykon/DreamShaper/blob/main/DreamShaper_8_pruned.safetensors) (about 2.13 GB, CreativeML OpenRAIL-M license; verified SHA-256 `879db523c30d3b9017143d56705015e15a2cb5628762c11d086fed9538abd7fd`). Review and comply with the model license before using it, especially commercially.
4. Start the image engine using the bundled `resources\start_comfyui.ps1` script or the `MYRA Image Engine` Startup shortcut. It binds only to `127.0.0.1:8188`, starts hidden, uses `--lowvram --cpu-vae`, and writes logs to `%LOCALAPPDATA%\MYRA\logs`.
5. Check `/image_status` in Telegram or the image status endpoint. It should report ComfyUI online and list the installed checkpoint.

## Telegram commands

- `/image <prompt>`
- `/imagine <prompt>`
- `/gerar <prompt>`
- `/image_status`
- Natural language, e.g. “Gere uma imagem de um farol na costa irlandesa”.

Image generation runs in a background worker. The bot remains responsive and sends the completed image as a Telegram photo.

## Troubleshooting

- Offline: start ComfyUI and check `http://127.0.0.1:8188/system_stats`.
- No checkpoint: confirm the `.safetensors` file is inside `ComfyUI\models\checkpoints`, then restart ComfyUI.
- Out of memory: keep 512×512, reduce steps, close other GPU-heavy apps, and retain `--lowvram --cpu-vae`.
- Logs: `%LOCALAPPDATA%\MYRA\logs\comfyui.stdout.log` and `comfyui.stderr.log`.
- Stop only the ComfyUI process started by MYRA with `resources\stop_comfyui.ps1`.

ComfyUI and checkpoints are intentionally separate from the MYRA installer because they are large and depend on the user's GPU, driver and model-license choices.
