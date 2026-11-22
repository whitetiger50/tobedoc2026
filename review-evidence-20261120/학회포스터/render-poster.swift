import Foundation
import AppKit
import CoreText
import CoreGraphics
struct Label: Decodable {
    var name,t: String
    var x,y,size,w,h: CGFloat
    var bold: Bool
    var color: String
    var url: String?
}
struct Shape: Decodable {var name,color:String;var x,y,w,h:CGFloat}
struct Matrix: Decodable {
    var name:String
    var x,y,rh,fs:CGFloat
    var widths:[CGFloat]
    var values:[[String]]
}
struct Poster: Decodable {
    var w,h: CGFloat
    var background:String
    var rects:[Shape]
    var texts:[Label]
    var tables:[Matrix]
}
let args=CommandLine.arguments
let poster=try JSONDecoder().decode(Poster.self,from:Data(contentsOf:URL(fileURLWithPath:args[1])))
func color(_ h:String)->CGColor {
    let i=Int(h.dropFirst(),radix:16)!
    return CGColor(srgbRed:CGFloat(i >> 16)/255,green:CGFloat((i >> 8) & 255)/255,blue:CGFloat(i & 255)/255,alpha:1)
}
let a2width:CGFloat=841*72/25.4, a2height:CGFloat=1189*72/25.4
var box=CGRect(x:0,y:0,width:a2width,height:a2height)
let consumer=CGDataConsumer(url:URL(fileURLWithPath:args[2]) as CFURL)!
let meta=[kCGPDFContextTitle as String:"MindCraft | 조현병 모의 환자의 영어 면담 발화"] as CFDictionary
let ctx=CGContext(consumer:consumer,mediaBox:&box,meta)!
ctx.beginPDFPage(nil)
ctx.scaleBy(x:a2width/poster.w,y:a2height/poster.h)
func rect(_ x:CGFloat,_ top:CGFloat,_ w:CGFloat,_ h:CGFloat,_ c:String){
    ctx.setFillColor(color(c));ctx.fill(CGRect(x:x,y:poster.h-top-h,width:w,height:h))
}
var fails=0
func label(_ string:String, _ x:CGFloat, _ y:CGFloat, _ fs:CGFloat, _ available:CGFloat, _ bold:Bool, _ c:String, _ center:Bool=false, _ name:String="", _ link:String?=nil) {
    let font=CTFontCreateWithName((bold ? "AppleSDGothicNeo-Bold":"AppleSDGothicNeo-Regular") as CFString,fs,nil)
    let attr=NSAttributedString(string:string,attributes:[.font:font,.foregroundColor:NSColor(cgColor:color(c))!])
    let line=CTLineCreateWithAttributedString(attr)
    let width=CGFloat(CTLineGetTypographicBounds(line,nil,nil,nil))
    if width>available {print("WIDTH",name,Int(width),">",Int(available));fails+=1}
    let actualX=center ? x+(available-width)/2:x
    ctx.textPosition=CGPoint(x:actualX,y:poster.h-y-fs)
    CTLineDraw(line,ctx)
    if let link=link {ctx.setURL(URL(string:link)! as CFURL,for: CGRect(x:actualX*a2width/poster.w,y:(poster.h-y-fs*1.2)*a2height/poster.h,width:width*a2width/poster.w,height:fs*1.4*a2height/poster.h))}
}
rect(0,0,poster.w,poster.h,poster.background)
for r in poster.rects {rect(r.x,r.y,r.w,r.h,r.color)}
for t in poster.texts {label(t.t,t.x,t.y,t.size,t.w,t.bold,t.color,false,t.name,t.url)}
for table in poster.tables {
    for (i,row) in table.values.enumerated() {
        let top=table.y+CGFloat(i)*table.rh
        var x=table.x
        let fill=i==0 ? "#075C55":(i%2==0 ? "#EFF3EF":"#FAFBF7")
        for (j,s) in row.enumerated() {
            let w=table.widths[j];rect(x,top,w,table.rh,fill)
            label(s,x+12,top+(table.rh-table.fs*1.15)/2-1,table.fs,w-24,i==0 || j==0,i==0 ? "#FFFFFF":"#152F32",j>0,"table:"+s)
            x+=w
        }
        rect(table.x,top+table.rh-1,table.widths.reduce(0,+),1,"#D6DFDA")
    }
}
ctx.endPDFPage();ctx.closePDF()
if fails>0 {exit(1)}

