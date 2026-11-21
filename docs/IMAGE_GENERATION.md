# MYRA — local image generation and vision

## Image understanding

1. Install a multimodal Ollama model, for example `qwen2.5vl:3b`.
2. Set `MYRA_VISION_MODEL=qwen2.5vl:3b` if using a different model.
3. In the native MYRA chat, attach one or more images and ask a question.
4. In Telegram, send a photo with an optional caption. MYRA downloads it and forwards it to the local vision model.

## Image generation

MYRA uses ComfyUI locally. No hosted image API or per-image service is required. The current tested profile is RTX A2000 Laptop 4 GB VRAM, ComfyUI low-VRAM mode, Realistic Vision V6.0 B1 SD 1.5, and the Stability AI SD VAE. See [COMFYUI_SETUP.md](COMFYUI_SETUP.md) for downloads, checksums, setup and model licensing.

Before generation, MYRA uses local Ollama `qwen2.5:3b-instruct-q5_K_M` on CPU as a literal Portuguese/English translator for SD 1.5. It must not embellish, invent settings, poses or accessories, or convert requested nudity into lingerie or clothing. If Ollama is unavailable, the original prompt is used unchanged. The response records both the original and translated prompt and the translation status.

The negative prompt removes rendering defects and non-photographic styles. It excludes nudity only when the user did not request nudity, to avoid the model introducing it into unrelated portraits. This behavior is a fidelity default, not a blanket censorship filter. The model license and applicable safety boundaries still apply.

Recommended tested sampler: DPM++ 2M SDE / Karras, 25–30 steps, CFG 5.5. Start with 512×768 portraits or 640×640 square images on 4 GB VRAM. Generation resolution and speed depend on hardware and model.

Telegram supports `/image <prompt>`, `/imagine <prompt>`, `/gerar <prompt>`, `/image_status`, and natural-language image requests. Generation runs in the background and sends the resulting photo to the chat.

## Image model licensing and remote services

“Local” means inference runs on the user's computer without hosted image inference charges. It does not mean that model weights have no license conditions. Review the upstream model card and license before use, especially commercial use. Hosted APIs are not silently used as a fallback.

## Troubleshooting

- ComfyUI offline: start it and verify `http://127.0.0.1:8188/system_stats`.
- Checkpoint missing: install the checkpoint in `ComfyUI/models/checkpoints`.
- VAE missing: install the VAE in `ComfyUI/models/vae`.
- Out of memory: lower dimensions and steps, close other GPU-heavy applications, and use ComfyUI low-VRAM mode.
- Vision model missing: run `ollama pull qwen2.5vl:3b` or select an installed multimodal model.
