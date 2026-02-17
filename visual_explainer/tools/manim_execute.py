import glob
import os
import shutil
import subprocess
import tempfile
from typing import Union


def execute_manim_code(code, scene_id: int, video_path: Union[str, os.PathLike], timeout: int = 30) -> tuple[bool, str]:
    """With a True boolean, you get the video_path. With false, you get the error associated to the code rendering."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_script = os.path.join(temp_dir, f"script_scene_{scene_id}.py")
        
        with open(temp_script, "w") as f:
            f.write(code) 
        
        try:
            res = subprocess.run(
                ["manim", "-ql", "-v", "WARNING", f"script_scene_{scene_id}.py"],
                cwd=temp_dir, 
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if res.returncode == 0:
                generated_videos = glob.glob(os.path.join(temp_dir, "media", "**", "*.mp4"), recursive=True)
                
                if generated_videos:
                    os.makedirs(os.path.dirname(video_path), exist_ok=True)     # Check if the folder exists first, otherwise we get the No Directory found error

                    # Then move the first found video to our controlled path
                    shutil.move(generated_videos[0], video_path)
                    
                    print(f"[Scene {scene_id}] Video successfully saved to: {video_path}\n")
                    return True, video_path
                else:
                    print(f"[{scene_id}] Error: Manim code executed successfully but no .mp4 file was generated.")
                    return False, "Error: Manim code executed successfully but no .mp4 file was generated."
            else:
                error_msg = res.stderr or res.stdout
                print(f"[{scene_id}] Execution Error:\n{error_msg[-100:]}\n")
                return False, f"Error:\n{error_msg}"

        except subprocess.TimeoutExpired:
            return False, f"Execution timed out. Code took longer than {timeout} seconds to execute, revise the code accordingly, keeping the details of the old scene in mind."
        except Exception as e:
            return False, f"System error during execution: {str(e)}"
               
             
if __name__ == "__main__":
    code = """
from manim import *

class SquareToCircle(Scene):
    def construct(self):
        square = Square()
        circle = Circle()
        
        self.play(Create(square))
        self.play(square.animate.rotate(PI / 4))
        self.play(Transform(square, circle))
        self.play(circle.animate.set_fill(LIGHT_PINK, opacity=0.5))
    """
    
    VIDEO_OUTPUT_DIR = os.path.join(os.path.abspath(os.path.curdir), "outputs", "videos")
    os.makedirs(VIDEO_OUTPUT_DIR, exist_ok=True)
    res = execute_manim_code(code, 1, os.path.join(VIDEO_OUTPUT_DIR, "scene_1.mp4"))
    print(res)