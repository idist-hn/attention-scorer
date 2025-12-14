"""
GPU utilities and optimization for AI processing.
"""

import os
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GPUInfo:
    """GPU information container."""
    available: bool = False
    device_id: int = 0
    name: str = "Unknown"
    memory_total_mb: float = 0.0
    memory_used_mb: float = 0.0
    memory_free_mb: float = 0.0
    cuda_version: str = ""
    compute_capability: Tuple[int, int] = (0, 0)


def check_gpu_availability() -> GPUInfo:
    """Check GPU availability and return info."""
    info = GPUInfo()
    
    try:
        import torch
        
        if torch.cuda.is_available():
            info.available = True
            info.device_id = torch.cuda.current_device()
            info.name = torch.cuda.get_device_name(info.device_id)
            
            props = torch.cuda.get_device_properties(info.device_id)
            info.memory_total_mb = props.total_memory / (1024 * 1024)
            info.compute_capability = (props.major, props.minor)
            
            # Get memory usage
            info.memory_used_mb = torch.cuda.memory_allocated(info.device_id) / (1024 * 1024)
            info.memory_free_mb = info.memory_total_mb - info.memory_used_mb
            
            info.cuda_version = torch.version.cuda or ""
            
            logger.info(f"GPU available: {info.name} with {info.memory_total_mb:.0f}MB")
        else:
            logger.info("GPU not available, using CPU")
            
    except ImportError:
        logger.warning("PyTorch not installed, GPU check skipped")
    except Exception as e:
        logger.error(f"Error checking GPU: {e}")
    
    return info


def get_optimal_device() -> str:
    """Get the optimal device for AI processing."""
    info = check_gpu_availability()
    
    if info.available:
        return f"cuda:{info.device_id}"
    
    # Check for MPS (Apple Silicon)
    try:
        import torch
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            logger.info("Using Apple MPS backend")
            return "mps"
    except ImportError:
        pass
    
    return "cpu"


def optimize_torch_settings() -> None:
    """Apply optimal PyTorch settings for inference."""
    try:
        import torch
        
        # Enable cudnn benchmarking for optimal convolution algorithms
        if torch.cuda.is_available():
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.enabled = True
            logger.info("CUDA optimizations enabled")
        
        # Set inference mode
        torch.set_grad_enabled(False)
        
        # Optimize memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("PyTorch optimizations applied")
        
    except ImportError:
        logger.warning("PyTorch not available for optimization")
    except Exception as e:
        logger.error(f"Error optimizing PyTorch: {e}")


def set_memory_fraction(fraction: float = 0.8) -> None:
    """Set maximum GPU memory fraction to use."""
    try:
        import torch
        
        if torch.cuda.is_available():
            torch.cuda.set_per_process_memory_fraction(fraction)
            logger.info(f"GPU memory fraction set to {fraction}")
            
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Error setting memory fraction: {e}")


def get_memory_stats() -> dict:
    """Get current GPU memory statistics."""
    stats = {
        'allocated_mb': 0.0,
        'reserved_mb': 0.0,
        'max_allocated_mb': 0.0
    }
    
    try:
        import torch
        
        if torch.cuda.is_available():
            device = torch.cuda.current_device()
            stats['allocated_mb'] = torch.cuda.memory_allocated(device) / (1024 * 1024)
            stats['reserved_mb'] = torch.cuda.memory_reserved(device) / (1024 * 1024)
            stats['max_allocated_mb'] = torch.cuda.max_memory_allocated(device) / (1024 * 1024)
            
    except ImportError:
        pass
    
    return stats


def clear_gpu_cache() -> None:
    """Clear GPU memory cache."""
    try:
        import torch
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            logger.debug("GPU cache cleared")
            
    except ImportError:
        pass

