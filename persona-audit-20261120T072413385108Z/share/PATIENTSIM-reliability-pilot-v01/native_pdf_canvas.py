"""Record page primitives and render them with macOS CoreText, including CFF fonts."""
from pathlib import Path
import json
import subprocess


def rgb(color):
    return [float(color.red), float(color.green), float(color.blue)]


class NativeCanvas:
    def __init__(self, filename, pagesize):
        self.filename = str(filename)
        self.width, self.height = pagesize
        self.operations = []
        self.fill = [0, 0, 0]
        self.stroke = [0, 0, 0]
        self.line_width = 1
        self.title = "Team brief"

    def setTitle(self, title):
        self.title = title

    def setAuthor(self, author):
        pass

    def setSubject(self, subject):
        pass

    def setFillColor(self, color):
        self.fill = rgb(color)

    def setStrokeColor(self, color):
        self.stroke = rgb(color)

    def setLineWidth(self, width):
        self.line_width = width

    def rect(self, x, y, w, h, fill=0, stroke=1):
        self.operations.append(dict(kind="rect", x=x, y=y, w=w, h=h,
                                    fill=self.fill if fill else None,
                                    stroke=self.stroke if stroke else None, lineWidth=self.line_width))

    def line(self, x1, y1, x2, y2):
        self.operations.append(dict(kind="line", x1=x1, y1=y1, x2=x2, y2=y2,
                                    color=self.stroke, lineWidth=self.line_width))

    def paragraph(self, text, x, top, w, size, leading, color, max_height):
        self.operations.append(dict(kind="text", text=text, x=x, top=top, w=w,
                                    size=size, leading=leading, color=rgb(color), maxHeight=max_height))

    def strong(self, text, x, baseline, size, color):
        self.operations.append(dict(kind="strong", text=text, x=x, baseline=baseline,
                                    size=size, color=rgb(color)))

    def showPage(self):
        pass

    def save(self):
        root = Path(__file__).resolve().parent
        spec = root / "team-brief-native-commands.json"
        spec.write_text(json.dumps(dict(width=self.width, height=self.height, title=self.title,
                                        operations=self.operations), ensure_ascii=False, indent=2) + "\n")
        subprocess.run(["/usr/bin/swift", "-module-cache-path", "/private/tmp/tobedoc-swift-cache",
                        str(root / "render_native_pdf.swift"), str(spec), self.filename,
                        str(root / "native-font-render-check.json")], check=True)
