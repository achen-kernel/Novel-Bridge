package com.achen.novelbridge.server.service;

import lombok.AllArgsConstructor;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Splits raw book text into chapters using {@code 第X回} pattern.
 * <p>
 * MOCK/DEBT: Uses simple regex splitting. Will be replaced by a Python splitter
 * in Demo 5 for books with non-standard chapter formats (e.g. Shan Hai Jing).
 */
public final class ChapterSplitter {

    private ChapterSplitter() { /* utility class */ }

    /** Pattern: 第 + Chinese numeral or digit + 回, rest of line as title */
    private static final Pattern CHAPTER_PATTERN =
            Pattern.compile("第([一二三四五六七八九十百千\\d]+)回[^\\n]*");

    /**
     * Split full text into chapter segments.
     *
     * @param content the complete book text
     * @return ordered list of chapter segments (chapter number, title, raw content)
     */
    public static List<ChapterSegment> split(String content) {
        Matcher matcher = CHAPTER_PATTERN.matcher(content);
        List<Match> matches = new ArrayList<>();

        while (matcher.find()) {
            matches.add(new Match(matcher.start(), matcher.end(),
                    chineseToInt(matcher.group(1)), matcher.group().strip()));
        }

        if (matches.isEmpty()) {
            return List.of();
        }

        List<ChapterSegment> segments = new ArrayList<>(matches.size());
        for (int i = 0; i < matches.size(); i++) {
            Match m = matches.get(i);
            int contentEnd = (i + 1 < matches.size()) ? matches.get(i + 1).start : content.length();
            String rawContent = content.substring(m.start, contentEnd);

            segments.add(new ChapterSegment(m.number, m.title, rawContent));
        }

        return segments;
    }

    /**
     * Convert Chinese numeral string to integer.
     * Supports 一~九, 十~九十九, 一百~九百九十九.
     */
    static int chineseToInt(String chinese) {
        // Try parsing as Arabic numeral first
        try {
            return Integer.parseInt(chinese.trim());
        } catch (NumberFormatException ignored) {
            // continue with Chinese numeral parsing
        }

        int result = 0;
        int current = 0;

        for (int i = 0; i < chinese.length(); i++) {
            char c = chinese.charAt(i);
            int digit = charValue(c);
            if (digit >= 0) {
                current = digit;
            } else if (c == '十') {
                current = (current == 0 ? 1 : current);
                result += current * 10;
                current = 0;
            } else if (c == '百') {
                current = (current == 0 ? 1 : current);
                result += current * 100;
                current = 0;
            } else if (c == '千') {
                current = (current == 0 ? 1 : current);
                result += current * 1000;
                current = 0;
            }
        }
        result += current;
        return result;
    }

    private static int charValue(char c) {
        return switch (c) {
            case '零' -> 0;
            case '一' -> 1;
            case '二' -> 2;
            case '三' -> 3;
            case '四' -> 4;
            case '五' -> 5;
            case '六' -> 6;
            case '七' -> 7;
            case '八' -> 8;
            case '九' -> 9;
            default -> -1;
        };
    }

    // ---- internal types ----

    @Data
    @AllArgsConstructor
    private static class Match {
        int start, end, number;
        String title;
    }

    /**
     * Result of splitting a single chapter.
     */
    @Data
    @AllArgsConstructor
    public static class ChapterSegment {
        /** 1-based chapter number */
        private int number;
        /** Chapter title extracted from the heading line */
        private String title;
        /** Raw text content of the chapter (includes heading line) */
        private String rawContent;
    }
}
