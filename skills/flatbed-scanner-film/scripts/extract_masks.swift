import Foundation
import Vision
import CoreImage

let args = CommandLine.arguments
guard args.count >= 3 else {
    fputs("usage: extract_masks <in_dir> <out_dir>\n", stderr)
    exit(2)
}
let inDir = args[1]
let outDir = args[2]
try FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)

let files = try FileManager.default.contentsOfDirectory(atPath: inDir)
    .filter { $0.hasSuffix(".png") }
    .sorted()

let ctx = CIContext()
let cs = CGColorSpace(name: CGColorSpace.linearGray)!

for (idx, fname) in files.enumerated() {
    autoreleasepool {
        let inURL = URL(fileURLWithPath: (inDir as NSString).appendingPathComponent(fname))
        let outURL = URL(fileURLWithPath: (outDir as NSString).appendingPathComponent(fname))
        guard let ci = CIImage(contentsOf: inURL) else { return }
        let req = VNGenerateForegroundInstanceMaskRequest()
        let handler = VNImageRequestHandler(ciImage: ci)
        do {
            try handler.perform([req])
            if let r = req.results?.first, !r.allInstances.isEmpty {
                let maskBuf = try r.generateScaledMaskForImage(forInstances: r.allInstances, from: handler)
                let maskCI = CIImage(cvPixelBuffer: maskBuf)
                try ctx.writePNGRepresentation(of: maskCI, to: outURL, format: .L8, colorSpace: cs)
            } else {
                let black = CIImage(color: CIColor.black).cropped(to: ci.extent)
                try ctx.writePNGRepresentation(of: black, to: outURL, format: .L8, colorSpace: cs)
            }
        } catch {
            fputs("mask error on \(fname): \(error)\n", stderr)
        }
        if (idx + 1) % 40 == 0 || idx + 1 == files.count {
            print("Masked \(idx + 1)/\(files.count)")
            fflush(stdout)
        }
    }
}
print("ALL MASKS DONE")
