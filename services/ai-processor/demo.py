#!/usr/bin/env python3
"""
Demo script for Attention Detection Pipeline.

This script demonstrates the attention detection system using webcam
or video file input.

Usage:
    python demo.py                    # Use webcam
    python demo.py --video path.mp4   # Use video file
    python demo.py --no-display       # Run without display (for testing)
"""

import argparse
import sys
import cv2
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")


def parse_args():
    parser = argparse.ArgumentParser(description="Attention Detection Demo")
    parser.add_argument(
        "--video", "-v",
        type=str,
        default=None,
        help="Path to video file. If not provided, webcam is used."
    )
    parser.add_argument(
        "--camera", "-c",
        type=int,
        default=0,
        help="Camera index (default: 0)"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="Frame width (default: 1280)"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=720,
        help="Frame height (default: 720)"
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Run without displaying video"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output video path"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Import here to allow --help without loading heavy modules
    from src.pipeline import AttentionPipeline
    from src.utils import VideoCapture, Visualizer
    
    # Initialize components
    logger.info("Starting Attention Detection Demo")
    
    pipeline = AttentionPipeline()
    visualizer = Visualizer()
    
    # Determine video source
    source = args.video if args.video else args.camera
    
    # Open video capture
    cap = VideoCapture(
        source=source,
        width=args.width,
        height=args.height
    )
    
    if not cap.open():
        logger.error("Failed to open video source")
        return 1
    
    # Setup video writer if output specified
    writer = None
    if args.output:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(
            args.output,
            fourcc,
            30,
            (args.width, args.height)
        )
    
    logger.info("Press 'q' to quit, 'r' to reset tracking")
    
    try:
        frame_count = 0
        
        for frame in cap.frames():
            frame_count += 1
            
            # Process frame
            result = pipeline.process_frame(frame, meeting_id="demo")
            
            # Draw results
            output_frame = visualizer.draw_results(frame, result)
            
            # Log periodic stats
            if frame_count % 100 == 0:
                avg_attention = 0
                if result.attention_results:
                    avg_attention = sum(r.attention_score for r in result.attention_results) / len(result.attention_results)
                logger.info(
                    f"Frame {frame_count}: {len(result.attention_results)} faces, "
                    f"avg attention: {avg_attention:.1f}%, "
                    f"processing: {result.processing_time_ms:.1f}ms"
                )
            
            # Write output
            if writer:
                writer.write(output_frame)
            
            # Display
            if not args.no_display:
                cv2.imshow("Attention Detection Demo", output_frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    logger.info("Quit requested")
                    break
                elif key == ord('r'):
                    pipeline.reset()
                    logger.info("Tracking reset")
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    
    finally:
        # Cleanup
        cap.release()
        if writer:
            writer.release()
        if not args.no_display:
            cv2.destroyAllWindows()
        pipeline.release()
    
    logger.info(f"Processed {frame_count} frames")
    return 0


if __name__ == "__main__":
    sys.exit(main())

