import QtQuick
import QtQuick.Controls

import "." as Design

Row {
    id: root

    property int score: 1
    property int maximum: 5
    property string dimensionName: "评分"
    property int hoveredScore: 0
    signal scoreSelected(int score)

    spacing: 0

    Repeater {
        id: starRepeater
        model: root.maximum
        delegate: ToolButton {
            id: starButton
            required property int index

            implicitWidth: Design.Theme.controlHeight
            implicitHeight: Design.Theme.controlHeight
            hoverEnabled: true
            ToolTip.visible: hovered
            ToolTip.text: "设为 " + (index + 1) + " 星"
            onHoveredChanged: {
                if (hovered)
                    root.hoveredScore = index + 1
                else if (root.hoveredScore === index + 1)
                    root.hoveredScore = 0
            }
            onClicked: root.scoreSelected(index + 1)

            Keys.onLeftPressed: {
                if (index > 0)
                    starRepeater.itemAt(index - 1).forceActiveFocus()
            }
            Keys.onRightPressed: {
                if (index + 1 < root.maximum)
                    starRepeater.itemAt(index + 1).forceActiveFocus()
            }

            contentItem: Label {
                readonly property int displayScore: root.hoveredScore > 0
                                                    ? root.hoveredScore
                                                    : root.score
                text: index < displayScore ? "★" : "☆"
                color: index < displayScore
                       ? Design.Theme.accent
                       : Design.Theme.textSecondary
                font.family: Design.Theme.fontFamily
                font.pixelSize: 22
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            background: Rectangle {
                radius: Design.Theme.radiusMedium
                color: starButton.down ? Design.Theme.controlPressed
                       : starButton.hovered ? Design.Theme.accentSubtle
                                        : "transparent"

                Design.AppFocusFrame {
                    active: starButton.visualFocus
                }
            }
        }
    }
}
