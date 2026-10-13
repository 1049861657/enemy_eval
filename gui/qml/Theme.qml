pragma Singleton

import QtQuick

QtObject {
    readonly property string fontFamily: "Microsoft YaHei UI"
    readonly property int space1: 4
    readonly property int space2: 8
    readonly property int space3: 12
    readonly property int space4: 16
    readonly property int space5: 24
    readonly property int radiusSmall: 4
    readonly property int radiusMedium: 8
    readonly property int radiusLarge: 12
    readonly property int controlHeight: 36
    readonly property int iconSize: 20
    readonly property color accent: "#0078D4"
    readonly property color accentHover: "#005FB8"
    readonly property color accentPressed: "#004C91"
    readonly property color danger: "#C42B1C"
    readonly property color dangerHover: "#A4262C"
    readonly property color dangerSubtle: "#FDEDEA"
    readonly property color success: "#107C10"
    readonly property color successSubtle: "#EAF6EA"
    readonly property color warning: "#9D5D00"
    readonly property color warningSubtle: "#FFF4CE"
    readonly property color accentSubtle: "#EAF3FB"
    readonly property color textOnAccent: "#FFFFFF"
    readonly property color textPrimary: "#1B1B1F"
    readonly property color textSecondary: "#5F6368"
    readonly property color textPlaceholder: "#9AA0A6"
    readonly property color surface: "#FFFFFF"
    readonly property color surfaceSubtle: "#F5F5F5"
    readonly property color fieldSurface: "#FBFBFB"
    readonly property color fieldHover: "#F7F7F7"
    readonly property color surfaceCanvas: "#ECECEC"
    readonly property color previewWell: "#DCDCDC"
    readonly property color border: "#D1D1D1"
    readonly property color borderHover: "#A8A8A8"
    readonly property color borderStrong: "#8A8A8A"
    readonly property color disabledSurface: "#EDEDED"
    readonly property color disabledText: "#5F6368"
    readonly property color overlay: "#52000000"
    readonly property color controlHover: "#E9E9E9"
    readonly property color controlPressed: "#DDEEFF"
    readonly property color popupSurface: "#FFFFFF"
    readonly property color optionHover: "#F3F3F3"
    readonly property color optionSelected: "#EAF3FB"
    readonly property color optionSelectedHover: "#DCECF8"
    readonly property color tabTrack: "#EDEDED"
    readonly property color tabHover: "#E2E2E2"
    readonly property color tabPressed: "#D8D8D8"
    readonly property color tabSelected: "#FFFFFF"
    readonly property int comboOptionHeight: 40
    readonly property int comboPopupMaxHeight: 300
    readonly property int titleFontSize: 20
    readonly property int bodyFontSize: 14
    readonly property int captionFontSize: 12

    signal lightDismiss()
}
