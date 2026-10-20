pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../components"
import ".." as Design

ScrollView {
    id: root

    required property var workspace

    clip: true
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

    ColumnLayout {
        width: root.availableWidth
        spacing: Design.Theme.space3
        AppSection {
            title: "异常抗性"
            Layout.fillWidth: true
            GridLayout {
                columns: 3
                width: parent.width
                Repeater {
                    model: ["冻结", "沉默", "晕眩", "沉睡", "浮空", "战栗", "恐惧", "麻痹", "诱导"]
                    delegate: CheckBox {
                        id: resistanceBox
                        required property string modelData
                        text: resistanceBox.modelData
                        checked: (root.workspace.enemyData.abnormal_resistances || {})[resistanceBox.modelData] > 0
                        onToggled: root.workspace.controller.updateResistance(
                            resistanceBox.modelData, checked ? 1.0 : 0.0)
                    }
                }
            }
        }
    }
}
