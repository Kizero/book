#import <Foundation/Foundation.h>
#import <PDFKit/PDFKit.h>
#import <Vision/Vision.h>
#import <CoreGraphics/CoreGraphics.h>
#import <AppKit/AppKit.h>

@interface Options : NSObject
@property (nonatomic, copy) NSString *inputPath;
@property (nonatomic, copy, nullable) NSString *outputPath;
@property (nonatomic) NSInteger directTextThreshold;
@property (nonatomic, copy) NSArray<NSString *> *ocrLanguages;
@property (nonatomic) CGFloat dpi;
@property (nonatomic) BOOL forceOCR;
@property (nonatomic) BOOL verbose;
@property (nonatomic) NSInteger startPage;
@property (nonatomic) NSInteger endPage;
@property (nonatomic, copy, nullable) NSString *debugImageDir;
@end

@implementation Options
@end

static void PrintUsage(void) {
    fprintf(
        stderr,
        "Usage:\n"
        "  pdf-to-txt <input.pdf> [-o output.txt] [--dpi 220] [--ocr-languages zh-Hans,en-US]\n"
        "             [--direct-text-threshold 20] [--start-page 1] [--end-page 10]\n"
        "             [--debug-image-dir ./debug-images] [--force-ocr] [--verbose]\n\n"
        "Notes:\n"
        "  - Each page first tries direct text extraction.\n"
        "  - If a page contains little or no embedded text, OCR is used automatically.\n"
        "  - OCR tries Vision first, then falls back to Tesseract when needed.\n"
        "  - Default OCR languages are zh-Hans and en-US.\n"
    );
}

static void StderrPrint(NSString *message) {
    fprintf(stderr, "%s\n", message.UTF8String);
}

static NSString *NormalizeExtractedText(NSString *text) {
    NSArray<NSString *> *lines = [text componentsSeparatedByCharactersInSet:NSCharacterSet.newlineCharacterSet];
    NSMutableArray<NSString *> *trimmedLines = [NSMutableArray arrayWithCapacity:lines.count];
    for (NSString *line in lines) {
        [trimmedLines addObject:[line stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceCharacterSet]];
    }
    NSString *joined = [trimmedLines componentsJoinedByString:@"\n"];
    return [joined stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
}

static NSInteger MeaningfulCharacterCount(NSString *text) {
    NSCharacterSet *whitespace = NSCharacterSet.whitespaceAndNewlineCharacterSet;
    NSCharacterSet *controls = NSCharacterSet.controlCharacterSet;
    NSInteger count = 0;
    for (NSUInteger index = 0; index < text.length; index++) {
        unichar value = [text characterAtIndex:index];
        if (![whitespace characterIsMember:value] && ![controls characterIsMember:value]) {
            count += 1;
        }
    }
    return count;
}

static NSString *DefaultOutputPath(NSString *inputPath) {
    NSString *directory = [inputPath stringByDeletingLastPathComponent];
    NSString *fileName = [[[inputPath lastPathComponent] stringByDeletingPathExtension] stringByAppendingPathExtension:@"txt"];
    return [directory stringByAppendingPathComponent:fileName];
}

static Options *ParseOptions(NSArray<NSString *> *arguments, NSError **error) {
    if (arguments.count == 0) {
        if (error) {
            *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Missing input PDF path."}];
        }
        return nil;
    }

    Options *options = [Options new];
    options.directTextThreshold = 20;
    options.ocrLanguages = @[ @"zh-Hans", @"en-US" ];
    options.dpi = 220;
    options.startPage = 1;
    options.endPage = 0;

    NSUInteger index = 0;
    while (index < arguments.count) {
        NSString *argument = arguments[index];

        if ([argument isEqualToString:@"-h"] || [argument isEqualToString:@"--help"]) {
            PrintUsage();
            exit(0);
        } else if ([argument isEqualToString:@"-o"] || [argument isEqualToString:@"--output"]) {
            index += 1;
            if (index >= arguments.count) {
                if (error) {
                    *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: [NSString stringWithFormat:@"Missing value after %@.", argument]}];
                }
                return nil;
            }
            options.outputPath = arguments[index];
        } else if ([argument isEqualToString:@"--dpi"]) {
            index += 1;
            if (index >= arguments.count) {
                if (error) {
                    *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Missing value after --dpi."}];
                }
                return nil;
            }
            CGFloat dpi = (CGFloat)[arguments[index] doubleValue];
            if (dpi <= 0) {
                if (error) {
                    *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Invalid DPI value."}];
                }
                return nil;
            }
            options.dpi = dpi;
        } else if ([argument isEqualToString:@"--ocr-languages"]) {
            index += 1;
            if (index >= arguments.count) {
                if (error) {
                    *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Missing value after --ocr-languages."}];
                }
                return nil;
            }
            NSMutableArray<NSString *> *languages = [NSMutableArray array];
            for (NSString *rawPart in [arguments[index] componentsSeparatedByString:@","]) {
                NSString *part = [rawPart stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
                if (part.length > 0) {
                    [languages addObject:part];
                }
            }
            if (languages.count == 0) {
                if (error) {
                    *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: @"OCR languages cannot be empty."}];
                }
                return nil;
            }
            options.ocrLanguages = languages;
        } else if ([argument isEqualToString:@"--direct-text-threshold"]) {
            index += 1;
            if (index >= arguments.count) {
                if (error) {
                    *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Missing value after --direct-text-threshold."}];
                }
                return nil;
            }
            NSInteger threshold = [arguments[index] integerValue];
            if (threshold < 0) {
                if (error) {
                    *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Invalid direct text threshold."}];
                }
                return nil;
            }
            options.directTextThreshold = threshold;
        } else if ([argument isEqualToString:@"--start-page"]) {
            index += 1;
            if (index >= arguments.count) {
                if (error) {
                    *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Missing value after --start-page."}];
                }
                return nil;
            }
            NSInteger startPage = [arguments[index] integerValue];
            if (startPage < 1) {
                if (error) {
                    *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Invalid start page."}];
                }
                return nil;
            }
            options.startPage = startPage;
        } else if ([argument isEqualToString:@"--end-page"]) {
            index += 1;
            if (index >= arguments.count) {
                if (error) {
                    *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Missing value after --end-page."}];
                }
                return nil;
            }
            NSInteger endPage = [arguments[index] integerValue];
            if (endPage < 1) {
                if (error) {
                    *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Invalid end page."}];
                }
                return nil;
            }
            options.endPage = endPage;
        } else if ([argument isEqualToString:@"--force-ocr"]) {
            options.forceOCR = YES;
        } else if ([argument isEqualToString:@"--debug-image-dir"]) {
            index += 1;
            if (index >= arguments.count) {
                if (error) {
                    *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Missing value after --debug-image-dir."}];
                }
                return nil;
            }
            options.debugImageDir = arguments[index];
        } else if ([argument isEqualToString:@"--verbose"]) {
            options.verbose = YES;
        } else if ([argument hasPrefix:@"-"]) {
            if (error) {
                *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: [NSString stringWithFormat:@"Unknown option: %@", argument]}];
            }
            return nil;
        } else if (options.inputPath == nil) {
            options.inputPath = argument;
        } else {
            if (error) {
                *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: [NSString stringWithFormat:@"Unexpected extra argument: %@", argument]}];
            }
            return nil;
        }

        index += 1;
    }

    if (options.inputPath == nil) {
        if (error) {
            *error = [NSError errorWithDomain:@"pdf-to-txt" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Missing input PDF path."}];
        }
        return nil;
    }

    return options;
}

static CGImageRef _Nullable RenderPageImage(PDFPage *page, CGFloat dpi) {
    CGRect bounds = [page boundsForBox:kPDFDisplayBoxMediaBox];
    CGFloat scale = dpi / 72.0;
    size_t width = (size_t)MAX(1.0, ceil(bounds.size.width * scale));
    size_t height = (size_t)MAX(1.0, ceil(bounds.size.height * scale));

    CGColorSpaceRef colorSpace = CGColorSpaceCreateDeviceRGB();
    CGContextRef context = CGBitmapContextCreate(NULL, width, height, 8, 0, colorSpace, kCGImageAlphaPremultipliedLast);
    CGColorSpaceRelease(colorSpace);
    if (context == NULL) {
        return NULL;
    }

    CGContextSetRGBFillColor(context, 1, 1, 1, 1);
    CGContextFillRect(context, CGRectMake(0, 0, width, height));
    CGContextSetInterpolationQuality(context, kCGInterpolationHigh);

    CGContextSaveGState(context);
    CGContextScaleCTM(context, scale, scale);
    CGContextTranslateCTM(context, -bounds.origin.x, -bounds.origin.y);
    [page drawWithBox:kPDFDisplayBoxMediaBox toContext:context];
    CGContextRestoreGState(context);

    CGImageRef image = CGBitmapContextCreateImage(context);
    CGContextRelease(context);
    return image;
}

static NSString *_Nullable OCRTextFromImage(CGImageRef image, NSArray<NSString *> *languages, NSError **error) {
    VNRecognizeTextRequest *request = [[VNRecognizeTextRequest alloc] init];
    request.recognitionLevel = VNRequestTextRecognitionLevelAccurate;
    request.usesLanguageCorrection = YES;
    request.recognitionLanguages = languages;
    if (@available(macOS 13.0, *)) {
        request.automaticallyDetectsLanguage = YES;
    }

    VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCGImage:image options:@{}];
    BOOL success = [handler performRequests:@[ request ] error:error];
    if (!success) {
        return nil;
    }

    NSArray<VNRecognizedTextObservation *> *results = request.results ?: @[];
    NSArray<VNRecognizedTextObservation *> *sorted = [results sortedArrayUsingComparator:^NSComparisonResult(VNRecognizedTextObservation *left, VNRecognizedTextObservation *right) {
        CGFloat leftTop = CGRectGetMaxY(left.boundingBox);
        CGFloat rightTop = CGRectGetMaxY(right.boundingBox);
        if (fabs(leftTop - rightTop) > 0.02) {
            return leftTop > rightTop ? NSOrderedAscending : NSOrderedDescending;
        }
        CGFloat leftX = CGRectGetMinX(left.boundingBox);
        CGFloat rightX = CGRectGetMinX(right.boundingBox);
        if (leftX < rightX) {
            return NSOrderedAscending;
        }
        if (leftX > rightX) {
            return NSOrderedDescending;
        }
        return NSOrderedSame;
    }];

    NSMutableArray<NSString *> *lines = [NSMutableArray arrayWithCapacity:sorted.count];
    for (VNRecognizedTextObservation *observation in sorted) {
        NSArray<VNRecognizedText *> *candidates = [observation topCandidates:1];
        VNRecognizedText *candidate = candidates.firstObject;
        if (candidate == nil) {
            continue;
        }
        NSString *line = [candidate.string stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
        if (line.length > 0) {
            [lines addObject:line];
        }
    }

    return [[lines componentsJoinedByString:@"\n"] stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
}

static BOOL WriteDebugImage(CGImageRef image, NSString *path, NSError **error) {
    NSBitmapImageRep *representation = [[NSBitmapImageRep alloc] initWithCGImage:image];
    NSData *data = [representation representationUsingType:NSBitmapImageFileTypePNG properties:@{}];
    if (data == nil) {
        if (error) {
            *error = [NSError errorWithDomain:@"pdf-to-txt" code:3 userInfo:@{NSLocalizedDescriptionKey: @"Failed to encode debug PNG."}];
        }
        return NO;
    }
    return [data writeToFile:path options:NSDataWritingAtomic error:error];
}

static NSString *MapLanguageForTesseract(NSString *language) {
    static NSDictionary<NSString *, NSString *> *mapping;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        mapping = @{
            @"zh-Hans": @"chi_sim",
            @"zh_CN": @"chi_sim",
            @"zh-CN": @"chi_sim",
            @"zh-Hant": @"chi_tra",
            @"zh_TW": @"chi_tra",
            @"zh-TW": @"chi_tra",
            @"en": @"eng",
            @"en-US": @"eng",
            @"en_GB": @"eng",
            @"en-GB": @"eng"
        };
    });
    return mapping[language] ?: language;
}

static NSArray<NSString *> *TesseractLanguages(NSArray<NSString *> *languages) {
    NSMutableOrderedSet<NSString *> *mapped = [NSMutableOrderedSet orderedSet];
    for (NSString *language in languages) {
        NSString *candidate = MapLanguageForTesseract(language);
        if (candidate.length > 0) {
            [mapped addObject:candidate];
        }
    }
    if (mapped.count == 0) {
        [mapped addObject:@"chi_sim"];
        [mapped addObject:@"eng"];
    }
    return mapped.array;
}

static NSString *TesseractExecutablePath(void) {
    NSArray<NSString *> *candidates = @[ @"/opt/homebrew/bin/tesseract", @"/usr/local/bin/tesseract", @"/usr/bin/tesseract" ];
    for (NSString *candidate in candidates) {
        if ([[NSFileManager defaultManager] isExecutableFileAtPath:candidate]) {
            return candidate;
        }
    }
    return @"tesseract";
}

static NSString *_Nullable OCRTextWithTesseract(NSString *imagePath, NSArray<NSString *> *languages, NSError **error) {
    NSString *languageArgument = [[TesseractLanguages(languages) componentsJoinedByString:@"+"] copy];
    NSTask *task = [[NSTask alloc] init];
    task.executableURL = [NSURL fileURLWithPath:TesseractExecutablePath()];
    task.arguments = @[ imagePath, @"stdout", @"-l", languageArgument, @"--psm", @"3" ];

    NSPipe *stdoutPipe = [NSPipe pipe];
    NSPipe *stderrPipe = [NSPipe pipe];
    task.standardOutput = stdoutPipe;
    task.standardError = stderrPipe;

    NSError *launchError = nil;
    if (![task launchAndReturnError:&launchError]) {
        if (error) {
            *error = launchError;
        }
        return nil;
    }

    [task waitUntilExit];
    NSData *stdoutData = [[stdoutPipe fileHandleForReading] readDataToEndOfFile];
    NSData *stderrData = [[stderrPipe fileHandleForReading] readDataToEndOfFile];

    if (task.terminationStatus != 0) {
        NSString *stderrText = [[NSString alloc] initWithData:stderrData encoding:NSUTF8StringEncoding];
        if (stderrText.length == 0) {
            stderrText = [[NSString alloc] initWithData:stderrData encoding:NSASCIIStringEncoding];
        }
        if (error) {
            *error = [NSError errorWithDomain:@"pdf-to-txt" code:4 userInfo:@{
                NSLocalizedDescriptionKey: stderrText.length > 0 ? stderrText : @"tesseract exited with a non-zero status."
            }];
        }
        return nil;
    }

    NSString *output = [[NSString alloc] initWithData:stdoutData encoding:NSUTF8StringEncoding];
    if (output.length == 0) {
        output = [[NSString alloc] initWithData:stdoutData encoding:NSASCIIStringEncoding];
    }
    return [output stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
}

static NSString *_Nullable OCRTextWithFallbacks(CGImageRef image, NSString *_Nullable imagePath, NSArray<NSString *> *languages, BOOL verbose, NSError **error) {
    NSError *primaryError = nil;
    NSString *primaryText = OCRTextFromImage(image, languages, &primaryError);
    if (MeaningfulCharacterCount(primaryText ?: @"") > 0) {
        return primaryText;
    }

    if (verbose) {
        if (primaryError != nil) {
            StderrPrint([NSString stringWithFormat:@"Primary OCR attempt failed: %@", primaryError.localizedDescription]);
        } else {
            StderrPrint(@"Primary OCR attempt returned no text, retrying with Tesseract.");
        }
    }

    NSString *temporaryImagePath = nil;
    NSString *resolvedImagePath = imagePath;
    NSError *imageWriteError = nil;
    if (resolvedImagePath.length == 0) {
        temporaryImagePath = [NSTemporaryDirectory() stringByAppendingPathComponent:[NSString stringWithFormat:@"pdf-to-txt-%@.png", NSUUID.UUID.UUIDString]];
        if (!WriteDebugImage(image, temporaryImagePath, &imageWriteError)) {
            if (error) {
                *error = imageWriteError;
            }
            return nil;
        }
        resolvedImagePath = temporaryImagePath;
    }

    NSError *tesseractError = nil;
    NSString *tesseractText = OCRTextWithTesseract(resolvedImagePath, languages, &tesseractError);
    if (temporaryImagePath.length > 0) {
        [[NSFileManager defaultManager] removeItemAtPath:temporaryImagePath error:nil];
    }

    if (MeaningfulCharacterCount(tesseractText ?: @"") > 0) {
        return tesseractText;
    }

    if (error != NULL) {
        *error = tesseractError ?: primaryError;
    }
    return tesseractText;
}

static BOOL Run(Options *options, NSError **error) {
    BOOL isDirectory = NO;
    if (![[NSFileManager defaultManager] fileExistsAtPath:options.inputPath isDirectory:&isDirectory] || isDirectory) {
        if (error) {
            *error = [NSError errorWithDomain:@"pdf-to-txt" code:2 userInfo:@{NSLocalizedDescriptionKey: [NSString stringWithFormat:@"Input file does not exist: %@", options.inputPath]}];
        }
        return NO;
    }

    if (![[[options.inputPath pathExtension] lowercaseString] isEqualToString:@"pdf"]) {
        if (error) {
            *error = [NSError errorWithDomain:@"pdf-to-txt" code:2 userInfo:@{NSLocalizedDescriptionKey: @"Input must be a PDF file."}];
        }
        return NO;
    }

    NSURL *inputURL = [NSURL fileURLWithPath:options.inputPath];
    PDFDocument *document = [[PDFDocument alloc] initWithURL:inputURL];
    if (document == nil) {
        if (error) {
            *error = [NSError errorWithDomain:@"pdf-to-txt" code:2 userInfo:@{NSLocalizedDescriptionKey: [NSString stringWithFormat:@"Failed to open PDF: %@", options.inputPath]}];
        }
        return NO;
    }

    if (document.isLocked) {
        if (error) {
            *error = [NSError errorWithDomain:@"pdf-to-txt" code:2 userInfo:@{NSLocalizedDescriptionKey: @"PDF is locked or encrypted and cannot be processed."}];
        }
        return NO;
    }

    NSString *outputPath = options.outputPath ?: DefaultOutputPath(options.inputPath);
    NSInteger totalPages = document.pageCount;
    NSInteger startPage = MIN(MAX(options.startPage, 1), MAX(totalPages, 1));
    NSInteger endPage = options.endPage > 0 ? MIN(options.endPage, totalPages) : totalPages;
    if (startPage > endPage) {
        if (error) {
            *error = [NSError errorWithDomain:@"pdf-to-txt" code:2 userInfo:@{NSLocalizedDescriptionKey: @"start-page cannot be greater than end-page."}];
        }
        return NO;
    }

    if (options.debugImageDir.length > 0) {
        NSError *directoryError = nil;
        BOOL created = [[NSFileManager defaultManager] createDirectoryAtPath:options.debugImageDir withIntermediateDirectories:YES attributes:nil error:&directoryError];
        if (!created) {
            if (error) {
                *error = directoryError ?: [NSError errorWithDomain:@"pdf-to-txt" code:2 userInfo:@{NSLocalizedDescriptionKey: @"Failed to create debug image directory."}];
            }
            return NO;
        }
    }

    NSMutableArray<NSString *> *pageContents = [NSMutableArray arrayWithCapacity:(NSUInteger)MAX(totalPages, 0)];

    for (NSInteger pageIndex = startPage - 1; pageIndex < endPage; pageIndex++) {
        @autoreleasepool {
            PDFPage *page = [document pageAtIndex:pageIndex];
            NSString *extractedText = NormalizeExtractedText(page.string ?: @"");
            NSInteger extractedCount = MeaningfulCharacterCount(extractedText);
            NSInteger pageNumber = pageIndex + 1;
            NSString *pageText = extractedText;

            if (options.verbose) {
                StderrPrint([NSString stringWithFormat:@"Page %ld/%ld: direct text count = %ld", (long)pageNumber, (long)totalPages, (long)extractedCount]);
            } else {
                StderrPrint([NSString stringWithFormat:@"Processing page %ld/%ld...", (long)pageNumber, (long)totalPages]);
            }

            if (!options.forceOCR && extractedCount >= options.directTextThreshold) {
                [pageContents addObject:pageText];
            } else {
                CGImageRef image = RenderPageImage(page, options.dpi);
                if (image != NULL) {
                    NSString *savedImagePath = nil;
                    if (options.debugImageDir.length > 0) {
                        NSString *imageName = [NSString stringWithFormat:@"page-%04ld.png", (long)pageNumber];
                        NSString *imagePath = [options.debugImageDir stringByAppendingPathComponent:imageName];
                        NSError *debugImageError = nil;
                        if (WriteDebugImage(image, imagePath, &debugImageError)) {
                            savedImagePath = imagePath;
                        } else if (options.verbose && debugImageError != nil) {
                            StderrPrint([NSString stringWithFormat:@"Failed to save debug image for page %ld: %@", (long)pageNumber, debugImageError.localizedDescription]);
                        }
                    }

                    NSError *ocrError = nil;
                    NSString *recognizedText = OCRTextWithFallbacks(image, savedImagePath, options.ocrLanguages, options.verbose, &ocrError);
                    CGImageRelease(image);

                    if (recognizedText != nil && MeaningfulCharacterCount(recognizedText) > 0) {
                        pageText = recognizedText;
                    } else if (options.verbose && ocrError != nil) {
                        StderrPrint([NSString stringWithFormat:@"OCR failed on page %ld: %@", (long)pageNumber, ocrError.localizedDescription]);
                    }
                }

                [pageContents addObject:pageText];
            }
        }
    }

    NSString *finalText = [pageContents componentsJoinedByString:@"\n\n\f\n\n"];
    NSError *writeError = nil;
    BOOL wrote = [finalText writeToURL:[NSURL fileURLWithPath:outputPath] atomically:YES encoding:NSUTF8StringEncoding error:&writeError];
    if (!wrote) {
        if (error) {
            *error = writeError ?: [NSError errorWithDomain:@"pdf-to-txt" code:2 userInfo:@{NSLocalizedDescriptionKey: @"Failed to save output text file."}];
        }
        return NO;
    }

    StderrPrint([NSString stringWithFormat:@"Saved text to: %@", outputPath]);
    return YES;
}

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSMutableArray<NSString *> *arguments = [NSMutableArray array];
        for (int index = 1; index < argc; index++) {
            [arguments addObject:[NSString stringWithUTF8String:argv[index]]];
        }

        NSError *parseError = nil;
        Options *options = ParseOptions(arguments, &parseError);
        if (options == nil) {
            StderrPrint([NSString stringWithFormat:@"Error: %@", parseError.localizedDescription]);
            PrintUsage();
            return 1;
        }

        NSError *runError = nil;
        if (!Run(options, &runError)) {
            StderrPrint([NSString stringWithFormat:@"Error: %@", runError.localizedDescription]);
            return 1;
        }

        return 0;
    }
}
