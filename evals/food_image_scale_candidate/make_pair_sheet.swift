import AppKit
import Foundation

enum PairSheetError: Error {
    case badArguments
    case unreadableImage(String)
    case cannotCreateBitmap
    case cannotEncodePNG
}

let arguments = Array(CommandLine.arguments.dropFirst())
guard arguments.count >= 3, arguments.count % 2 == 1 else {
    throw PairSheetError.badArguments
}

let outputPath = arguments[0]
let records = stride(from: 1, to: arguments.count, by: 2).map {
    (label: arguments[$0], path: arguments[$0 + 1])
}
let columns = 5
let rows = Int(ceil(Double(records.count) / Double(columns)))
let cellWidth = 300
let cellHeight = 300
let sheetWidth = columns * cellWidth
let sheetHeight = rows * cellHeight

guard let bitmap = NSBitmapImageRep(
    bitmapDataPlanes: nil,
    pixelsWide: sheetWidth,
    pixelsHigh: sheetHeight,
    bitsPerSample: 8,
    samplesPerPixel: 4,
    hasAlpha: true,
    isPlanar: false,
    colorSpaceName: .deviceRGB,
    bitmapFormat: [],
    bytesPerRow: 0,
    bitsPerPixel: 0
), let context = NSGraphicsContext(bitmapImageRep: bitmap) else {
    throw PairSheetError.cannotCreateBitmap
}

NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = context
NSColor.white.setFill()
NSRect(x: 0, y: 0, width: sheetWidth, height: sheetHeight).fill()
context.imageInterpolation = .medium

let textAttributes: [NSAttributedString.Key: Any] = [
    .font: NSFont.monospacedSystemFont(ofSize: 13, weight: .semibold),
    .foregroundColor: NSColor.black,
]

for (index, record) in records.enumerated() {
    guard let image = NSImage(contentsOfFile: record.path) else {
        throw PairSheetError.unreadableImage(record.path)
    }
    let column = index % columns
    let row = index / columns
    let cellBottom = sheetHeight - (row + 1) * cellHeight
    record.label.draw(
        in: NSRect(
            x: column * cellWidth + 10,
            y: cellBottom + cellHeight - 24,
            width: cellWidth - 20,
            height: 18
        ),
        withAttributes: textAttributes
    )
    image.draw(
        in: NSRect(
            x: column * cellWidth + 10,
            y: cellBottom + 10,
            width: cellWidth - 20,
            height: cellHeight - 42
        ),
        from: .zero,
        operation: .copy,
        fraction: 1
    )
}
context.flushGraphics()
NSGraphicsContext.restoreGraphicsState()

guard let data = bitmap.representation(using: .png, properties: [:]) else {
    throw PairSheetError.cannotEncodePNG
}
try data.write(to: URL(fileURLWithPath: outputPath), options: .atomic)
