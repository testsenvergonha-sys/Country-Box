#pragma once
#include <stdint.h>

typedef enum {
    dsErrorFree = 0,
    dsFramePending = 1,
    dsRefLost = 2,
    dsBitstreamError = 4,
    dsDepLayerLost = 8,
    dsNoParamSets = 16,
    dsDataErrorConcealed = 32,
    dsInvalidArgument = 64,
    dsInitialLimit = 128
} DECODING_STATE;

typedef enum {
    ERROR_CON_DISABLE = 0,
    ERROR_CON_FRAME_COPY,
    ERROR_CON_SLICE_COPY,
    ERROR_CON_SLICE_COPY_CROSS_IDR_FREEZE_RES_CHANGE,
    ERROR_CON_SLICE_MV_COPY_CROSS_IDR,
    ERROR_CON_SLICE_MV_COPY_CROSS_IDR_FREEZE_RES_CHANGE
} ERROR_CON_IDC;

typedef enum {
    VIDEO_BITSTREAM_AVC = 0,
    VIDEO_BITSTREAM_SVC = 1,
    VIDEO_BITSTREAM_DEFAULT = VIDEO_BITSTREAM_SVC
} VIDEO_BITSTREAM_TYPE;

typedef struct {
    int iWidth;
    int iHeight;
    int iFormat;
    int iStride[2];
} SSystemBuffer;

typedef struct {
    SSystemBuffer sSystemBuffer;
} SUsrData;

typedef struct {
    int iBufferStatus;
    unsigned long long uiInBsTimeStamp;
    unsigned long long uiOutYuvTimeStamp;
    SUsrData UsrData;
    unsigned char *pDst[3];
} SBufferInfo;

typedef struct {
    VIDEO_BITSTREAM_TYPE eVideoBsType;
} SVideoProperty;

typedef struct {
    unsigned char uiTargetDqLayer;
    ERROR_CON_IDC eEcActiveIdc;
    SVideoProperty sVideoProperty;
    void *sVideoPropertyPad;
} SDecodingParam;

typedef const struct ISVCDecoderVtbl *ISVCDecoder;

struct ISVCDecoderVtbl {
    long (*Initialize)(ISVCDecoder *, const SDecodingParam *);
    long (*Uninitialize)(ISVCDecoder *);
    DECODING_STATE (*DecodeFrame)(ISVCDecoder *, const unsigned char *, const int, unsigned char **, int *, int *);
    DECODING_STATE (*DecodeFrameNoDelay)(ISVCDecoder *, const unsigned char *, const int, unsigned char **, SBufferInfo *);
    DECODING_STATE (*DecodeFrame2)(ISVCDecoder *, const unsigned char *, const int, unsigned char **, SBufferInfo *);
    DECODING_STATE (*DecodeParser)(ISVCDecoder *, const unsigned char *, const int, void *);
    DECODING_STATE (*DecodeFrameEx)(ISVCDecoder *, const unsigned char *, const int, unsigned char *, const int, int *, int *, int *);
    long (*SetOption)(ISVCDecoder *, int, void *);
    long (*GetOption)(ISVCDecoder *, int, void *);
};
