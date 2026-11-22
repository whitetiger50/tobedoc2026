import AppKit
import CoreText
import CoreGraphics
import Foundation

let args = CommandLine.arguments
guard args.count == 4 else { fatalError("commands.json output.pdf review.json") }
let data = try Data(contentsOf: URL(fileURLWithPath: args[1]))
let spec = try JSONSerialization.jsonObject(with: data) as! [String:Any]
let width = spec["width"] as! Double
let height = spec["height"] as! Double
let operations = spec["operations"] as! [[String:Any]]
var media = CGRect(x:0,y:0,width:width,height:height)
let info: [CFString:Any] = [kCGPDFContextTitle:spec["title"] as? String ?? "Team brief",
                           kCGPDFContextAuthor:"투비닥터 연구팀"]
guard let ctx = CGContext(URL(fileURLWithPath:args[2]) as CFURL, mediaBox:&media,
                          info as CFDictionary) else { fatalError("Cannot create PDF") }
ctx.beginPDFPage(nil)
ctx.setShouldAntialias(true)
var bounds = [[String:Any]]()

func color(_ rgb:[Double]) -> NSColor {
    NSColor(srgbRed:rgb[0],green:rgb[1],blue:rgb[2],alpha:1)
}
func hex(_ value:String) -> NSColor {
    let n=UInt32(value.replacingOccurrences(of:"#",with:""),radix:16) ?? 0
    return NSColor(srgbRed:Double((n>>16)&255)/255,green:Double((n>>8)&255)/255,
                   blue:Double(n&255)/255,alpha:1)
}
func attribute(_ tag:String,_ key:String) -> String? {
    let pattern=key+"=[\"']([^\"']+)[\"']"
    let r=try! NSRegularExpression(pattern:pattern)
    let s=tag as NSString
    guard let m=r.firstMatch(in:tag,range:NSRange(location:0,length:s.length)) else {return nil}
    return s.substring(with:m.range(at:1))
}
func attributed(_ html:String,font:NSFont,base:NSColor,leading:Double) -> NSAttributedString {
    let out=NSMutableAttributedString(string:"")
    let tags=try! NSRegularExpression(pattern:"<[^>]+>")
    let source=html as NSString
    var last=0
    var ink=base
    func append(_ s:String) {
        let decoded=s.replacingOccurrences(of:"&amp;",with:"&").replacingOccurrences(of:"&lt;",with:"<").replacingOccurrences(of:"&gt;",with:">")
        out.append(NSAttributedString(string:decoded,attributes:[.font:font,.foregroundColor:ink]))
    }
    for m in tags.matches(in:html,range:NSRange(location:0,length:source.length)) {
        if m.range.location>last {append(source.substring(with:NSRange(location:last,length:m.range.location-last)))}
        let tag=source.substring(with:m.range)
        if tag.hasPrefix("<br") { append("\n") }
        else if tag.hasPrefix("<font"),let h=attribute(tag,"color") {ink=hex(h)}
        else if tag.hasPrefix("<link"),let h=attribute(tag,"color") {ink=hex(h)}
        else if tag.hasPrefix("</font") || tag.hasPrefix("</link") {ink=base}
        last=m.range.location+m.range.length
    }
    if last<source.length {append(source.substring(from:last))}
    let ps=NSMutableParagraphStyle()
    ps.minimumLineHeight=leading
    ps.maximumLineHeight=leading
    ps.lineBreakMode = .byWordWrapping
    out.addAttribute(.paragraphStyle,value:ps,range:NSRange(location:0,length:out.length))
    return out
}

for op in operations {
    let kind=op["kind"] as! String
    if kind=="rect" {
        let box=CGRect(x:op["x"] as! Double,y:op["y"] as! Double,
                       width:op["w"] as! Double,height:op["h"] as! Double)
        if let fill=op["fill"] as? [Double] {ctx.setFillColor(color(fill).cgColor);ctx.fill(box)}
        if let stroke=op["stroke"] as? [Double] {
            ctx.setStrokeColor(color(stroke).cgColor);ctx.setLineWidth(op["lineWidth"] as! Double);ctx.stroke(box)
        }
    } else if kind=="line" {
        ctx.setStrokeColor(color(op["color"] as! [Double]).cgColor)
        ctx.setLineWidth(op["lineWidth"] as! Double)
        ctx.move(to:CGPoint(x:op["x1"] as! Double,y:op["y1"] as! Double))
        ctx.addLine(to:CGPoint(x:op["x2"] as! Double,y:op["y2"] as! Double));ctx.strokePath()
    } else if kind=="strong" {
        guard let font=NSFont(name:"AppleSDGothicNeo-Bold",size:op["size"] as! Double) else {fatalError("Required font missing")}
        let a=NSAttributedString(string:op["text"] as! String,attributes:[.font:font,.foregroundColor:color(op["color"] as! [Double])])
        ctx.textMatrix = .identity
        ctx.textPosition=CGPoint(x:op["x"] as! Double,y:op["baseline"] as! Double)
        CTLineDraw(CTLineCreateWithAttributedString(a),ctx)
    } else if kind=="text" {
        guard let font=NSFont(name:"AppleSDGothicNeo-Regular",size:op["size"] as! Double) else {fatalError("Required font missing")}
        let html=op["text"] as! String
        let a=attributed(html,font:font,base:color(op["color"] as! [Double]),leading:op["leading"] as! Double)
        let setter=CTFramesetterCreateWithAttributedString(a)
        let w=op["w"] as! Double
        let size=CTFramesetterSuggestFrameSizeWithConstraints(setter,CFRange(location:0,length:0),nil,CGSize(width:w,height:2000),nil)
        let h=ceil(size.height)
        if let max=op["maxHeight"] as? Double, h>max+1 {fatalError("Text overflow \(h) > \(max): \(html)")}
        let top=op["top"] as! Double
        let box=CGRect(x:op["x"] as! Double,y:top-h-1,width:w,height:h+1)
        let path=CGPath(rect:box,transform:nil)
        let frame=CTFramesetterCreateFrame(setter,CFRange(location:0,length:0),path,nil)
        let visible=CTFrameGetVisibleStringRange(frame)
        guard visible.length==a.length else {fatalError("Clipped text: \(html)")}
        ctx.textMatrix = .identity
        CTFrameDraw(frame,ctx)
        if html.hasPrefix("<link"),let href=attribute(html,"href"),let url=URL(string:href) {ctx.setURL(url as CFURL,for:box)}
        bounds.append(["label":String(a.string.prefix(65)),"top":top,"bottom":box.minY,"height":h])
    }
}
ctx.endPDFPage()
ctx.closePDF()
let review:[String:Any] = ["fontFamily":"Apple SD Gothic Neo","faces":["AppleSDGothicNeo-Regular","AppleSDGothicNeo-Bold"],"content_blocks":bounds]
try JSONSerialization.data(withJSONObject:review,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:args[3]))
print("Rendered one page with Apple SD Gothic Neo Regular/Bold")
