/*
 * hiscore.h - high score table and its backup RAM image. Portable C99, no libc beyond
 * stdint/stddef/string.
 *
 * Image layout, big endian (the 68000 byte order; serialised explicitly so the host test
 * matches the console):
 *   offset  size  field
 *      0     4    magic 'R' 'O' 'O' 'F' (0x524F4F46)
 *      4     2    version (1)
 *      6   120    10 entries, each: 8 name bytes, then score as u32
 *    126     4    checksum: FNV-1a 32 bit over bytes 0..125
 * Total HISCORE_IMAGE_SIZE = 130 bytes.
 */
#ifndef ROOFLINE_HISCORE_H
#define ROOFLINE_HISCORE_H

#include <stdint.h>
#include <stddef.h>

#define HISCORE_ENTRIES 10
#define HISCORE_NAME_LEN 8
#define HISCORE_MAGIC 0x524F4F46u
#define HISCORE_VERSION 1u
#define HISCORE_IMAGE_SIZE 130u

typedef struct {
    char name[HISCORE_ENTRIES][HISCORE_NAME_LEN]; /* space padded, not NUL terminated */
    uint32_t score[HISCORE_ENTRIES];              /* sorted, highest first */
} HiscoreTable;

/* Fill with the factory table (10000 down to 1000 in steps of 1000). */
void hiscore_defaults(HiscoreTable *t);

/* Load from a backup RAM image. Returns 1 when the image was valid. On any problem (short
 * buffer, bad magic, bad version, bad checksum) the table is set to defaults and 0 is
 * returned. */
int hiscore_load(HiscoreTable *t, const uint8_t *buf, size_t len);

/* Write the image into buf. Returns HISCORE_IMAGE_SIZE, or 0 when cap is too small. */
size_t hiscore_serialise(const HiscoreTable *t, uint8_t *buf, size_t cap);

/* Insert a score. Equal scores rank below existing ones. name is up to 8 characters (shorter
 * is space padded). Returns the zero based row (0 = first place, 9 = last place) or -1 when
 * the score does not make the table or is zero. */
int hiscore_insert(HiscoreTable *t, const char *name, uint32_t score);

#endif
