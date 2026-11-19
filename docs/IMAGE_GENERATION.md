# MYRA ? Local image generation and vision

## Image understanding

1. Install a multimodal Ollama model, for example `qwen2.5vl:3b`.
2. Set `MYRA_VISION_MODEL=qwen2.5vl:3b` in the MYRA runtime environment if using a different model.
3. In MYRA chat, use **? Imagem** to attach one or more images and ask a question.
4. In Telegram, send a photo with an optional caption. MYRA downloads it from Telegram and forwards it to the local vision model.

The native client converts large images to JPEG previews before upload. The backend currently accepts JPEG, PNG and WebP data URLs. Animated GIFs are converted to a still image in the desktop client.

## Image generation (free local inference)

MYRA uses ComfyUI locally. This avoids hosted API billing and does not require an API key. It is not bundled in the MYRA installer because ComfyUI and model checkpoints are large and hardware-dependent. For the Windows portable setup, low-VRAM launch script and the current 4 GB GPU profile, see `docs/COMFYUI_SETUP.md`.

1. Install ComfyUI using its official instructions: https://github.com/Comfy-Org/ComfyUI
2. Download an open-weight Stable Diffusion 1.5 checkpoint that you are licensed to use, and place the `.safetensors` file in `ComfyUI/models/checkpoints/`. A commonly used starting point is `v1-5-pruned-emaonly.safetensors` from the Stable Diffusion v1.5 model repository.
3. Start ComfyUI with its local server on `127.0.0.1:8188`.
4. Open MYRA, enter a prompt in the chat box and select **? Gerar imagem**. The first checkpoint listed by ComfyUI is used.
5. Telegram supports `/image <prompt>`, `/imagine <prompt>`, `/gerar <prompt>`, `/image_status`, and natural-language requests such as ?Gere uma imagem de um farol?. Generation runs in the background so chat polling stays responsive.

MYRA supports repeated generation requests; it does not impose an image-count quota. Actual throughput and resolution depend on available VRAM/RAM, disk space and the selected checkpoint. For machines with 4 GB VRAM, begin at 512?512 and use ComfyUI low-VRAM mode.

## Image model licensing and remote services

?Free? here means open-weight model files and local inference without per-image hosted API charges. Check each checkpoint's license and usage restrictions before commercial use. Hosted image APIs are not silently used as a fallback: current providers may require a user key and charge against a balance.

## Troubleshooting

- `ComfyUI local n?o est? dispon?vel`: start ComfyUI and verify `http://127.0.0.1:8188/system_stats`.
- `Nenhum checkpoint v?lido`: install a compatible checkpoint in `models/checkpoints` and restart/refresh ComfyUI.
- Out of memory: lower image dimensions, use a smaller checkpoint, or enable ComfyUI low-VRAM mode.
- Vision model not found: run `ollama pull qwen2.5vl:3b` or set `MYRA_VISION_MODEL` to an installed multimodal model.
