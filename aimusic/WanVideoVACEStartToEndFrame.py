import torch
import numpy as np
from comfy.utils import common_upscale
class WanVideoVACEStartToEndFrame:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "num_frames": ("INT",
                           {"default": 81, "min": 1, "max": 10000, "step": 4, "tooltip": "Number of frames to encode"}),
            "empty_frame_level": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01,
                                            "tooltip": "White level of empty frame to use"}),
        },
            "optional": {
                "start_image": ("IMAGE",),
                "end_image": ("IMAGE",),
                "control_images": ("IMAGE",),
                "inpaint_mask": ("MASK", {"tooltip": "Inpaint mask to use for the empty frames"}),
                "start_index": ("INT",
                                {"default": 0, "min": 0, "max": 10000, "step": 1, "tooltip": "Index to start from"}),
                "end_index": ("INT",
                              {"default": -1, "min": -10000, "max": 10000, "step": 1, "tooltip": "Index to end at"}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK",)
    RETURN_NAMES = ("images", "masks",)
    FUNCTION = "process"
    CATEGORY = "aimusic/WanVideoWrapper"
    DESCRIPTION = "Helper node to create start/end frame batch and masks for VACE"

    def process(self, num_frames, empty_frame_level, start_image=None, end_image=None, control_images=None,
                inpaint_mask=None, start_index=0, end_index=-1):

        if start_image is None and end_image is None and control_images is not None:
            if control_images.shape[0] >= num_frames:
                control_images = control_images[:num_frames]
            elif control_images.shape[0] < num_frames:
                # padd with empty_frame_level frames
                padding = torch.ones(
                    (num_frames - control_images.shape[0], control_images.shape[1], control_images.shape[2],
                     control_images.shape[3]), device=control_images.device) * empty_frame_level
                control_images = torch.cat([control_images, padding], dim=0)
            return (control_images.cpu().float(), torch.zeros_like(control_images[:, :, :, 0]).cpu().float())
        B, H, W, C = start_image.shape if start_image is not None else end_image.shape
        device = start_image.device if start_image is not None else end_image.device

        # Convert negative end_index to positive
        if end_index < 0:
            end_index = num_frames + end_index

        # Create output batch with empty frames
        out_batch = torch.ones((num_frames, H, W, 3), device=device) * empty_frame_level

        # Create mask tensor with proper dimensions
        masks = torch.ones((num_frames, H, W), device=device)

        # Pre-process all images at once to avoid redundant work
        if end_image is not None and (end_image.shape[1] != H or end_image.shape[2] != W):
            end_image = common_upscale(end_image.movedim(-1, 1), W, H, "lanczos", "disabled").movedim(1, -1)

        if control_images is not None and (control_images.shape[1] != H or control_images.shape[2] != W):
            control_images = common_upscale(control_images.movedim(-1, 1), W, H, "lanczos", "disabled").movedim(1, -1)

        # Place start image at start_index
        if start_image is not None:
            frames_to_copy = min(start_image.shape[0], num_frames - start_index)
            if frames_to_copy > 0:
                out_batch[start_index:start_index + frames_to_copy] = start_image[:frames_to_copy]
                masks[start_index:start_index + frames_to_copy] = 0

        # Place end image at end_index
        if end_image is not None:
            # Calculate where to start placing end images
            end_start = end_index - end_image.shape[0] + 1
            if end_start < 0:  # Handle case where end images won't all fit
                end_image = end_image[abs(end_start):]
                end_start = 0

            frames_to_copy = min(end_image.shape[0], num_frames - end_start)
            if frames_to_copy > 0:
                out_batch[end_start:end_start + frames_to_copy] = end_image[:frames_to_copy]
                masks[end_start:end_start + frames_to_copy] = 0

        # Apply control images to remaining frames that don't have start or end images
        if control_images is not None:
            # Create a mask of frames that are still empty (mask == 1)
            empty_frames = masks.sum(dim=(1, 2)) > 0.5 * H * W

            if empty_frames.any():
                # Only apply control images where they exist
                control_length = control_images.shape[0]
                for frame_idx in range(num_frames):
                    if empty_frames[frame_idx] and frame_idx < control_length:
                        out_batch[frame_idx] = control_images[frame_idx]

        # Apply inpaint mask if provided
        if inpaint_mask is not None:
            inpaint_mask = common_upscale(inpaint_mask.unsqueeze(1), W, H, "nearest-exact", "disabled").squeeze(1).to(
                device)

            # Handle different mask lengths efficiently
            if inpaint_mask.shape[0] > num_frames:
                inpaint_mask = inpaint_mask[:num_frames]
            elif inpaint_mask.shape[0] < num_frames:
                repeat_factor = (num_frames + inpaint_mask.shape[0] - 1) // inpaint_mask.shape[0]  # Ceiling division
                inpaint_mask = inpaint_mask.repeat(repeat_factor, 1, 1)[:num_frames]

            # Apply mask in one operation
            masks = inpaint_mask * masks

        return (out_batch.cpu().float(), masks.cpu().float())
