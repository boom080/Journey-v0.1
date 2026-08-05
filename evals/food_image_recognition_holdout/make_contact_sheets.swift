import AppKit
import Foundation

struct Entry {
    let id: String
    let cohort: String
    let localPath: String
    let label: String
    let sourceTitle: String
}

let scriptURL = URL(fileURLWithPath: #filePath)
let root = scriptURL.deletingLastPathComponent()
let manifest = root.appendingPathComponent("candidate_manifest.jsonl")
let outputDirectory = root.appendingPathComponent("assets/qa")
try FileManager.default.createDirectory(
    at: outputDirectory,
    withIntermediateDirectories: true
)

let data = try String(contentsOf: manifest, encoding: .utf8)
let entries: [Entry] = try data
    .split(separator: "\n")
    .map { line in
        let object = try JSONSerialization.jsonObject(with: Data(line.utf8)) as! [String: Any]
        let gold = object["gold"] as! [String: Any]
        let names = gold["names"] as! [[String: Any]]
        let label = (names.first?["canonical_en"] as? String).flatMap {
            $0.isEmpty ? nil : $0
        } ?? "NONFOOD"
        let source = object["source"] as! [String: Any]
        return Entry(
            id: object["id"] as! String,
            cohort: object["cohort"] as! String,
            localPath: object["local_path"] as! String,
            label: label,
            sourceTitle: source["file_title"] as! String
        )
    }

let grouped = Dictionary(grouping: entries, by: \.cohort)
let cellWidth = 300
let cellHeight = 250
let columns = 4
let imageRectHeight = 185

for cohort in grouped.keys.sorted() {
    let cohortEntries = grouped[cohort]!.sorted { $0.id < $1.id }
    let rows = Int(ceil(Double(cohortEntries.count) / Double(columns)))
    let canvasSize = NSSize(width: columns * cellWidth, height: rows * cellHeight)
    let image = NSImage(size: canvasSize)
    image.lockFocus()
    NSColor.white.setFill()
    NSRect(origin: .zero, size: canvasSize).fill()

    for (index, entry) in cohortEntries.enumerated() {
        let column = index % columns
        let row = index / columns
        let x = column * cellWidth
        let y = (rows - row - 1) * cellHeight
        let path = root.appendingPathComponent(entry.localPath)
        guard let sourceImage = NSImage(contentsOf: path) else {
            fatalError("Cannot load \(path.path)")
        }
        let available = NSRect(
            x: x + 10,
            y: y + 58,
            width: cellWidth - 20,
            height: imageRectHeight
        )
        let scale = min(
            available.width / sourceImage.size.width,
            available.height / sourceImage.size.height
        )
        let drawSize = NSSize(
            width: sourceImage.size.width * scale,
            height: sourceImage.size.height * scale
        )
        let drawRect = NSRect(
            x: available.midX - drawSize.width / 2,
            y: available.midY - drawSize.height / 2,
            width: drawSize.width,
            height: drawSize.height
        )
        sourceImage.draw(
            in: drawRect,
            from: .zero,
            operation: .sourceOver,
            fraction: 1.0
        )

        let paragraph = NSMutableParagraphStyle()
        paragraph.alignment = .center
        let idAttributes: [NSAttributedString.Key: Any] = [
            .font: NSFont.boldSystemFont(ofSize: 12),
            .foregroundColor: NSColor.black,
            .paragraphStyle: paragraph,
        ]
        let detailAttributes: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 9),
            .foregroundColor: NSColor.darkGray,
            .paragraphStyle: paragraph,
        ]
        NSString(string: "\(entry.id) · \(entry.label)").draw(
            in: NSRect(x: x + 6, y: y + 34, width: cellWidth - 12, height: 18),
            withAttributes: idAttributes
        )
        NSString(string: entry.sourceTitle).draw(
            in: NSRect(x: x + 6, y: y + 7, width: cellWidth - 12, height: 26),
            withAttributes: detailAttributes
        )
    }
    image.unlockFocus()

    guard
        let tiff = image.tiffRepresentation,
        let bitmap = NSBitmapImageRep(data: tiff),
        let png = bitmap.representation(using: .png, properties: [:])
    else {
        fatalError("Cannot encode sheet for \(cohort)")
    }
    try png.write(
        to: outputDirectory.appendingPathComponent("\(cohort).png"),
        options: .atomic
    )
    print("wrote \(cohort): \(cohortEntries.count) samples")
}
