#include "obj_pool.h"

void obj_pool_init(ObjPool *p, uint16_t sprite_base) {
    for (uint8_t i = 0; i < POOL_MAX; i++) {
        PoolObj z = {0};
        p->obj[i] = z;
        p->next_free[i] = (uint8_t)(i + 1 < POOL_MAX ? i + 1 : POOL_NONE);
    }
    p->free_head = 0;
    p->live = 0;
    p->peak = 0;
    p->hide = 0;
    p->sprite_base = sprite_base;
}

uint8_t obj_pool_alloc(ObjPool *p, uint8_t type, int32_t x, int32_t y, int32_t vx, int32_t vy) {
    uint8_t i = p->free_head;
    if (i == POOL_NONE) return POOL_NONE;
    p->free_head = p->next_free[i];
    p->next_free[i] = POOL_NONE;
    PoolObj *o = &p->obj[i];
    o->x = x; o->y = y; o->vx = vx; o->vy = vy;
    o->type = type;
    o->flags = POOL_F_LIVE;
    o->anim = 0;
    o->anim_tick = i; /* phase seed: obj_pool_anim reduces it mod the animation period, spreading frame changes (strip re-queues) over frames */
    p->hide &= ~((uint32_t)1 << i); /* reused before the view hid it: it draws over its own run */
    if (++p->live > p->peak) p->peak = p->live;
    return i;
}

void obj_pool_free(ObjPool *p, uint8_t i) {
    if (!obj_pool_is_live(p, i)) return;
    p->obj[i].flags = 0;
    p->next_free[i] = p->free_head;
    p->free_head = i;
    p->live--;
    p->hide |= (uint32_t)1 << i;
}

void obj_pool_step(ObjPool *p) {
    PoolObj *o = p->obj;
    for (uint8_t i = 0; i < POOL_MAX; i++, o++) {
        if (!(o->flags & POOL_F_LIVE)) continue;
        o->x += o->vx;
        o->y += o->vy;
    }
}

uint32_t obj_pool_take_hidden(ObjPool *p) {
    uint32_t m = p->hide;
    p->hide = 0;
    return m;
}
