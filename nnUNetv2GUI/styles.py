# styles.py
from tkinter import ttk

# Define constants
BG_COLOR = "#262626"
FONT_FAMILY = "Arial"  # Use a standard font
FONT_SIZE = 12
WINDOW_WIDTH = 850
WINDOW_HEIGHT =650
BUTTON_FONT_SIZE = 14  # Increase button font size
HOME_BUTTON_FONT_SIZE = 18 
BUTTON_PADDING = 10  # Add padding around the button

PADDING_X = 20
PADDING_Y = 20
TEXTBOX_WIDTH = 750
TEXTBOX_HEIGHT = 250
HOME_BUTTON_WIDTH = 120
HOME_BUTTON_HEIGHT = 40

def configure_styles():
    style = ttk.Style()

    # Configure button styles
    style.configure("ButtonStyle.TButton", font=(FONT_FAMILY, FONT_SIZE))
    style.configure("ButtonLabel.TLabel", background=BG_COLOR)
    style.configure("ButtonFrame.TFrame", background=BG_COLOR)

    # Corner image label style
    style.configure("CornerImageLabel.TLabel", background=BG_COLOR, borderwidth=0, highlightthickness=0)

    return style
