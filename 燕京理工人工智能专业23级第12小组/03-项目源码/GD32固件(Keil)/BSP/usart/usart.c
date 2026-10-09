#include "usart.h"

/* ---------------- 接收环形缓冲 (中断写入, 主循环读取) ---------------- */
#define RX_RING_SIZE 128
static volatile uint8_t  rx_ring[RX_RING_SIZE];
static volatile uint16_t rx_head = 0;          /* 中断写位置 */
static volatile uint16_t rx_tail = 0;          /* 主循环读位置 */

/* 解析器状态 */
typedef enum {
    ST_H0 = 0, ST_H1, ST_CMD, ST_LEN, ST_DATA, ST_SUM, ST_T0, ST_T1
} parse_state_t;

static parse_state_t st = ST_H0;
static uint8_t  rx_cmd = 0;
static uint8_t  rx_len = 0;
static uint8_t  rx_data[FRAME_MAX_DATA];
static uint8_t  rx_sum = 0;
static uint8_t  rx_idx = 0;

/* 完整帧暂存 */
static volatile uint8_t  frame_ready = 0;
static uint8_t  frame_cmd = 0;
static uint8_t  frame_data[FRAME_MAX_DATA];
static uint8_t  frame_len = 0;

void USART_CommInit(void)
{
    rcu_periph_clock_enable(COMM_GPIO_RCU);
    rcu_periph_clock_enable(COMM_USART_RCU);

    /* TX/RX 引脚复用 */
    gpio_af_set(COMM_GPIO_PORT, COMM_GPIO_AF, COMM_TX_PIN | COMM_RX_PIN);
    gpio_mode_set(COMM_GPIO_PORT, GPIO_MODE_AF, GPIO_PUPD_PULLUP,
                  COMM_TX_PIN | COMM_RX_PIN);
    gpio_output_options_set(COMM_GPIO_PORT, GPIO_OTYPE_PP, GPIO_OSPEED_50MHZ,
                            COMM_TX_PIN | COMM_RX_PIN);

    usart_deinit(COMM_USART);
    usart_baudrate_set(COMM_USART, COMM_BAUDRATE);
    usart_word_length_set(COMM_USART, USART_WL_8BIT);
    usart_stop_bit_set(COMM_USART, USART_STB_1BIT);
    usart_parity_config(COMM_USART, USART_PM_NONE);
    usart_hardware_flow_coherence_config(COMM_USART, USART_HCM_NONE);
    usart_transmit_config(COMM_USART, USART_TRANSMIT_ENABLE);
    usart_receive_config(COMM_USART, USART_RECEIVE_ENABLE);

    nvic_irq_enable(USART5_IRQn, 5, 0);
    usart_interrupt_enable(COMM_USART, USART_INT_RBNE);
    usart_enable(COMM_USART);
}

void USART_SendFrame(uint8_t cmd, const uint8_t *data, uint8_t len)
{
    uint8_t sum = cmd ^ len;
    uint8_t i;

    if (len > FRAME_MAX_DATA) return;
    for (i = 0; i < len; i++) sum ^= data[i];

    while (RESET == usart_flag_get(COMM_USART, USART_FLAG_TBE)) {}
    usart_data_transmit(COMM_USART, FRAME_HEAD0);
    while (RESET == usart_flag_get(COMM_USART, USART_FLAG_TBE)) {}
    usart_data_transmit(COMM_USART, FRAME_HEAD1);

    usart_data_transmit(COMM_USART, cmd);
    while (RESET == usart_flag_get(COMM_USART, USART_FLAG_TBE)) {}
    usart_data_transmit(COMM_USART, len);
    while (RESET == usart_flag_get(COMM_USART, USART_FLAG_TBE)) {}

    for (i = 0; i < len; i++) {
        usart_data_transmit(COMM_USART, data[i]);
        while (RESET == usart_flag_get(COMM_USART, USART_FLAG_TBE)) {}
    }

    usart_data_transmit(COMM_USART, sum);
    while (RESET == usart_flag_get(COMM_USART, USART_FLAG_TBE)) {}
    usart_data_transmit(COMM_USART, FRAME_TAIL0);
    while (RESET == usart_flag_get(COMM_USART, USART_FLAG_TBE)) {}
    usart_data_transmit(COMM_USART, FRAME_TAIL1);
}

/* 主循环调用的逐字节状态机, 与PC端 FrameParser 状态一一对应 */
static void parser_feed(uint8_t b)
{
    switch (st) {
    case ST_H0:
        if (b == FRAME_HEAD0) st = ST_H1;
        break;
    case ST_H1:
        st = (b == FRAME_HEAD1) ? ST_CMD : ST_H0;
        break;
    case ST_CMD:
        rx_cmd = b;
        rx_sum = b;
        rx_idx = 0;
        st = ST_LEN;
        break;
    case ST_LEN:
        rx_len = b;
        rx_sum ^= b;
        st = (b <= FRAME_MAX_DATA) ? ST_DATA : ST_H0;
        break;
    case ST_DATA:
        rx_data[rx_idx++] = b;
        rx_sum ^= b;
        if (rx_idx >= rx_len) st = ST_SUM;
        break;
    case ST_SUM:
        if (b == rx_sum) st = ST_T0;
        else             st = ST_H0;
        break;
    case ST_T0:
        st = (b == FRAME_TAIL0) ? ST_T1 : ST_H0;
        break;
    case ST_T1: {
        uint8_t k;
        st = ST_H0;
        if (b == FRAME_TAIL1 && !frame_ready) {
            frame_cmd = rx_cmd;
            frame_len = rx_len;
            for (k = 0; k < rx_len; k++) frame_data[k] = rx_data[k];
            frame_ready = 1;
        }
        break;
    }
    default:
        st = ST_H0;
        break;
    }
}

uint8_t USART_GetFrame(uint8_t *cmd, uint8_t *data, uint8_t *len)
{
    uint8_t i;
    /* 先把环形缓冲中已收到的数据全部喂给状态机 */
    while (rx_head != rx_tail) {
        uint8_t b = rx_ring[rx_tail];
        rx_tail = (uint16_t)((rx_tail + 1U) % RX_RING_SIZE);
        parser_feed(b);
    }

    if (frame_ready) {
        *cmd = frame_cmd;
        *len = frame_len;
        for (i = 0; i < frame_len; i++) data[i] = frame_data[i];
        frame_ready = 0;
        return 1;
    }
    return 0;
}

/* USART5 接收中断: 仅入环形缓冲, 不做解析(缩短中断耗时) */
void USART5_IRQHandler(void)
{
    if ((RESET != usart_interrupt_flag_get(COMM_USART, USART_INT_FLAG_RBNE)) &&
        (RESET != usart_flag_get(COMM_USART, USART_FLAG_RBNE))) {
        uint8_t b = (uint8_t)usart_data_receive(COMM_USART);
        uint16_t next = (uint16_t)((rx_head + 1U) % RX_RING_SIZE);
        if (next != rx_tail) {          /* 缓冲未满才写入 */
            rx_ring[rx_head] = b;
            rx_head = next;
        }
    }
}

/* printf 重定向到 USART5, 方便调试 */
int fputc(int ch, FILE *f)
{
    (void)f;
    usart_data_transmit(COMM_USART, (uint8_t)ch);
    while (RESET == usart_flag_get(COMM_USART, USART_FLAG_TBE)) {}
    return ch;
}
