import QtQuick
import QtQuick.Controls

import "." as Design

Row {
    id: root

    property int score: 1
    property int maximum: 5
    property string dimensionName: "评分"
    signal scoreSelected(int score)

    spacing: Design.Theme.space1

    Repeater {
        model: root.maximum
        delegate: ToolButton {
            required property int index
            text: index < root.score ? "★" : "☆"
            font.pixelSize: 20
            Accessible.name: root.dimensionName + "，设为 " + (index + 1) + " 星"
            ToolTip.visible: hovered
            ToolTip.text: "设为 " + (index + 1) + " 星"
            onClicked: root.scoreSelected(index + 1)
        }
    }
}
