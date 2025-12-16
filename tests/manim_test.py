from manim import *


class SquareToCircle(Scene):
    def construct(self):
        square = Square()
        circle = Circle()
        
        self.play(Create(square))
        self.play(square.animate.rotate(PI / 4))
        self.play(Transform(square, circle))
        self.play(circle.animate.set_fill(LIGHT_PINK, opacity=0.5))
        

# Run with "python -m manim -p manim_test.py SquareToCircle"