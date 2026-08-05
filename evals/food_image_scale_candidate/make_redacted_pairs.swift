import AppKit
import Foundation

struct TopLeftRect {
    let x: CGFloat
    let y: CGFloat
    let width: CGFloat
    let height: CGFloat
}

enum RedactionError: Error {
    case badArguments
    case unreadableImage(String)
    case cannotCreateBitmap
    case cannotEncodePNG
}

func drawRedacted(
    sourcePath: String,
    destinationPath: String,
    removeRuler: Bool
) throws {
    guard let source = NSImage(contentsOfFile: sourcePath),
          let cgImage = source.cgImage(forProposedRect: nil, context: nil, hints: nil)
    else {
        throw RedactionError.unreadableImage(sourcePath)
    }
    let width = cgImage.width
    let height = cgImage.height
    guard let bitmap = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: width,
        pixelsHigh: height,
        bitsPerSample: 8,
        samplesPerPixel: 4,
        hasAlpha: true,
        isPlanar: false,
        colorSpaceName: .deviceRGB,
        bitmapFormat: [],
        bytesPerRow: 0,
        bitsPerPixel: 0
    ), let context = NSGraphicsContext(bitmapImageRep: bitmap) else {
        throw RedactionError.cannotCreateBitmap
    }

    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = context
    context.imageInterpolation = .none
    let canvas = NSRect(x: 0, y: 0, width: width, height: height)
    NSImage(cgImage: cgImage, size: canvas.size).draw(
        in: canvas,
        from: .zero,
        operation: .copy,
        fraction: 1
    )

    // Neutral warm gray is visually distinct from food and contains no answer.
    NSColor(
        calibratedRed: 0.95,
        green: 0.93,
        blue: 0.91,
        alpha: 1
    ).setFill()

    var masks = [
        TopLeftRect(x: 320, y: 0, width: 220, height: 190),
        TopLeftRect(x: 135, y: 365, width: 190, height: 115),
    ]
    if removeRuler {
        masks.append(TopLeftRect(x: 360, y: 120, width: 140, height: 360))
    }
    for mask in masks {
        NSRect(
            x: mask.x,
            y: CGFloat(height) - mask.y - mask.height,
            width: mask.width,
            height: mask.height
        ).fill()
    }
    context.flushGraphics()
    NSGraphicsContext.restoreGraphicsState()

    guard let data = bitmap.representation(using: .png, properties: [:]) else {
        throw RedactionError.cannotEncodePNG
    }
    try data.write(to: URL(fileURLWithPath: destinationPath), options: .atomic)
}

guard CommandLine.arguments.count == 4 else {
    throw RedactionError.badArguments
}

let sourcePath = CommandLine.arguments[1]
try drawRedacted(
    sourcePath: sourcePath,
    destinationPath: CommandLine.arguments[2],
    removeRuler: false
)
try drawRedacted(
    sourcePath: sourcePath,
    destinationPath: CommandLine.arguments[3],
    removeRuler: true
)
