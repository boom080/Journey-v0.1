import AppKit
import Foundation

enum SheetError: Error {
    case badArguments
    case unreadableImage(String)
    case cannotCreateBitmap
    case cannotEncodePNG
}

let arguments = Array(CommandLine.arguments.dropFirst())
guard arguments.count >= 3, arguments.count % 2 == 1 else {
    throw SheetError.badArguments
}

let outputPath = arguments[0]
let records = stride(from: 1, to: arguments.count, by: 2).map {
    (label: arguments[$0], path: arguments[$0 + 1])
}
let columns = 5
let rows = Int(ceil(Double(records.count) / Double(columns)))
let cellWidth = 400
let cellHeight = 190
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
    throw SheetError.cannotCreateBitmap
}

NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = context
NSColor.white.setFill()
NSRect(x: 0, y: 0, width: sheetWidth, height: sheetHeight).fill()
context.imageInterpolation = .none

let textAttributes: [NSAttributedString.Key: Any] = [
    .font: NSFont.monospacedSystemFont(ofSize: 15, weight: .semibold),
    .foregroundColor: NSColor.black,
]

for (index, record) in records.enumerated() {
    guard let image = NSImage(contentsOfFile: record.path) else {
        throw SheetError.unreadableImage(record.path)
    }
    let column = index % columns
    let row = index / columns
    let cellBottom = sheetHeight - (row + 1) * cellHeight
    let labelRect = NSRect(
        x: column * cellWidth + 12,
        y: cellBottom + cellHeight - 28,
        width: cellWidth - 24,
        height: 22
    )
    record.label.draw(in: labelRect, withAttributes: textAttributes)

    // Original panels are 540x480. The scale display is in the bottom-center
    // region; AppKit source coordinates use a bottom-left origin.
    image.draw(
        in: NSRect(
            x: column * cellWidth + 12,
            y: cellBottom + 8,
            width: cellWidth - 24,
            height: cellHeight - 42
        ),
        from: NSRect(x: 135, y: 0, width: 190, height: 115),
        operation: .copy,
        fraction: 1
    )
}
context.flushGraphics()
NSGraphicsContext.restoreGraphicsState()

guard let data = bitmap.representation(using: .png, properties: [:]) else {
    throw SheetError.cannotEncodePNG
}
try data.write(to: URL(fileURLWithPath: outputPath), options: .atomic)
