import QtQuick
import QtQuick.Controls

import "." as Design

Rectangle {
    id: root

    property bool radarOn: false

    signal modePicked(bool radar)

    readonly property int inset: 2
    readonly property int glyph: 16

    implicitWidth: row.implicitWidth + inset * 2
    implicitHeight: row.implicitHeight + inset * 2
    width: implicitWidth
    height: implicitHeight
    radius: 6
    color: Design.Theme.tabTrack
    border.width: 1
    border.color: Design.Theme.border

    ButtonGroup {
        id: modeGroup

        exclusive: true
    }

    component Segment: ToolButton {
        id: seg

        required property bool radar

        ButtonGroup.group: modeGroup
        checkable: true
        hoverEnabled: true
        leftInset: 0
        rightInset: 0
        topInset: 0
        bottomInset: 0
        display: AbstractButton.TextBesideIcon
        font.family: Design.Theme.fontFamily
        font.pixelSize: Design.Theme.captionFontSize
        font.weight: Font.Medium
        icon.width: root.glyph
        icon.height: root.glyph
        icon.color: seg.checked ? Design.Theme.textOnAccent : Design.Theme.textSecondary
        palette.buttonText: seg.icon.color
        spacing: Design.Theme.space1
        leftPadding: Design.Theme.space2
        rightPadding: Design.Theme.space2
        topPadding: 5
        bottomPadding: 5
        implicitHeight: 26

        background: Rectangle {
            radius: 4
            color: {
                if (seg.checked) {
                    if (seg.down)
                        return Design.Theme.accentPressed
                    if (seg.hovered)
                        return Design.Theme.accentHover
                    return Design.Theme.accent
                }
                if (seg.down)
                    return Design.Theme.tabPressed
                if (seg.hovered)
                    return Design.Theme.tabHover
                return "transparent"
            }

            Design.AppFocusFrame {
                active: seg.visualFocus
            }
        }

        onClicked: {
            if (seg.radar !== root.radarOn)
                root.modePicked(seg.radar)
        }
    }

    Row {
        id: row

        x: root.inset
        y: root.inset
        spacing: 0

        Segment {
            id: radarBtn

            radar: true
            text: "雷达"
            icon.source: "icons/radar.svg"
        }

        Segment {
            id: cardsBtn

            radar: false
            text: "卡片"
            icon.source: "icons/cards.svg"
        }
    }

    Binding {
        target: radarBtn
        property: "checked"
        value: root.radarOn
        restoreMode: Binding.RestoreBindingOrValue
    }

    Binding {
        target: cardsBtn
        property: "checked"
        value: !root.radarOn
        restoreMode: Binding.RestoreBindingOrValue
    }
}
