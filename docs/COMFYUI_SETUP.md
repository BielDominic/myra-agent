# MYRA local image engine (Windows)

MYRA uses ComfyUI on loopback only for local image generation and editing. Image inference is not sent to a hosted image API.

## Hardware profile

The tested workstation uses an NVIDIA RTX A2000 Laptop GPU with 4 GB VRAM. ComfyUI runs with `--lowvram --cpu-vae`. Start at 512×768 for portraits or 640×640 for square images and 25–30 steps. Larger sizes may run out of memory or become slow.

## Recommended photorealistic model

The default checkpoint is [Realistic Vision V6.0 B1 (fp16, noVAE)](https://huggingface.co/SG161222/Realistic_Vision_V6.0_B1_noVAE). Its model card explicitly targets realism and photorealism and recommends an external VAE. The downloaded checkpoint is 2,132,625,894 bytes; locally verified SHA-256: `C48BFD159CD7A6507B128685E963C398FA72399CEFAFAF603781DF50CE836CC7`.

Install it in `ComfyUI\models\checkpoints\Realistic_Vision_V6.0_NV_B1_fp16.safetensors`.

Install the [Stability AI SD VAE](https://huggingface.co/stabilityai/sd-vae-ft-mse-original) file `vae-ft-mse-840000-ema-pruned.safetensors` in `ComfyUI\models\vae\`. Local SHA-256: `735E4C3A447A3255760D7F86845F09F937809BAA529C17370D83E4C3758F3C75`.

The earlier DreamShaper 8 checkpoint remains installed as a fallback. MYRA selects Realistic Vision by default when it is available.

## Prompt interpretation

Before generation, MYRA uses the installed local Ollama model `qwen2.5:3b-instruct-q5_K_M` on CPU as a literal translator for Portuguese/English requests for Stable Diffusion 1.5. It must not embellish or invent a setting, pose, accessories or other visual attributes. This does not consume the 4 GB GPU needed by ComfyUI. If Ollama is offline, the original prompt is passed through unchanged.

The negative prompt targets rendering defects and non-photographic styles. Nudity is excluded only when the request did not ask for it; explicit requested visual attributes are preserved. This is not a promise of unrestricted output: the model's own license and applicable safety limits still apply.

## Sampler profile

- Sampler: DPM++ 2M SDE
- Scheduler: Karras
- Steps: 25–30
- CFG: 5.5
- External VAE: `vae-ft-mse-840000-ema-pruned.safetensors`

## Install ComfyUI

1. Download the official [ComfyUI Windows portable NVIDIA package](https://github.com/Comfy-Org/ComfyUI/releases/download/v0.46.0/ComfyUI_windows_portable_nvidia.7z). The verified v0.46.0 archive SHA-256 is `6a5255c7ec01fdc54bdbd8e4507073cf6acda2fbeea74ae1829a50681af5fac6`.
2. Extract it into `%LOCALAPPDATA%\MYRA\ComfyUI`.
3. Install the checkpoint and VAE files listed above in their respective model folders.
4. Start ComfyUI using `resources\start_comfyui.ps1` or the MYRA Image Engine Startup shortcut. It binds only to `127.0.0.1:8188`.
5. Check `/image_status` in Telegram or `/images/status` in the local API.

## Telegram commands

- `/image <prompt>`
- `/imagine <prompt>`
- `/gerar <prompt>`
- `/image_status`
- Natural language, e.g. “Gere uma imagem de um farol na costa irlandesa”.

Image generation runs in a background worker. The bot remains responsive and sends the completed image as a Telegram photo.

## Troubleshooting

- Offline: start ComfyUI and check `http://127.0.0.1:8188/system_stats`.
- No checkpoint: confirm the `.safetensors` file is inside `models/checkpoints`.
- No VAE: confirm the VAE file is inside `models/vae`.
- Out of memory: reduce image size/steps, close other GPU-heavy apps, and retain `--lowvram --cpu-vae`.
- Logs: `%LOCALAPPDATA%\MYRA\logs\comfyui.stdout.log` and `comfyui.stderr.log`.
- Stop only the ComfyUI process started by MYRA with `resources\stop_comfyui.ps1`.

ComfyUI and model checkpoints remain separate from the MYRA installer because they are large and hardware-dependent. Review the [Realistic Vision model card and CreativeML OpenRAIL-M license](https://huggingface.co/SG161222/Realistic_Vision_V6.0_B1_noVAE) before use, especially commercial use. The license has use restrictions; do not treat “local” or “open-weight” as “unrestricted”.
