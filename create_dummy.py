import os
from reportlab.pdfgen import canvas

def create_dummy_pdf():
    c = canvas.Canvas("dummy_educational.pdf")
    c.drawString(100, 750, "Peblo Educational Content: Grade 3 Science")
    c.drawString(100, 730, "Photosynthesis is the process used by plants, algae and certain bacteria.")
    c.drawString(100, 710, "They harness energy from sunlight and turn it into chemical energy.")
    c.drawString(100, 690, "This process is vital for life on Earth, providing oxygen and food.")
    c.save()

if __name__ == "__main__":
    create_dummy_pdf()
