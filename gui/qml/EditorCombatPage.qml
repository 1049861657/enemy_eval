pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "." as Design

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
            title: "战斗属性"
            Layout.fillWidth: true
            GridLayout {
                columns: 2
                width: parent.width
                columnSpacing: Design.Theme.space3
                rowSpacing: Design.Theme.space2

                Repeater {
                    model: [
                        ["最大生命值", "max_hp", 1, 999999, 1, 0],
                        ["生命自回速度", "hp_recovery_speed", 0, 10000, 0.1, 1],
                        ["攻击力", "attack", 0, 999999, 1, 0],
                        ["攻击间隔", "attack_interval", 0.1, 10, 0.1, 1],
                        ["攻击范围半径", "attack_range_radius", 0, 10, 0.1, 1],
                        ["防御力", "defense", 0, 999999, 1, 0],
                        ["法术抗性", "magic_resistance", 0, 100, 1, 0],
                        ["损伤抗性", "damage_resistance", 0, 100, 1, 0],
                        ["元素抗性", "element_resistance", 0, 100, 1, 0],
                        ["移动速度", "move_speed", 0.1, 5, 0.01, 2],
                        ["重量等级", "weight_level", 0, 10, 1, 0],
                        ["基础嘲讽等级", "base_taunt_level", 0, 10, 1, 0],
                        ["目标价值", "target_value", 0, 50, 1, 0]
                    ]
                    delegate: Item {
                        id: combatStat
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.columnSpan: 2
                        implicitHeight: combatRow.implicitHeight
                        RowLayout {
                            id: combatRow
                            anchors.fill: parent
                            Label {
                                text: combatStat.modelData[0]
                                Layout.preferredWidth: 130
                            }
                            AppNumberField {
                                Layout.fillWidth: true
                                enabled: combatStat.modelData[1] !== "attack_range_radius"
                                         || (root.workspace.enemyData.attack_type !== "近战"
                                             && root.workspace.enemyData.attack_type !== "不攻击")
                                value: Number(root.workspace.enemyData[combatStat.modelData[1]] ?? 0)
                                minimum: combatStat.modelData[2]
                                maximum: combatStat.modelData[3]
                                stepSize: combatStat.modelData[4]
                                decimals: combatStat.modelData[5]
                                hasError: root.workspace.fieldErrors[combatStat.modelData[1]] !== undefined
                                errorText: root.workspace.fieldErrors[combatStat.modelData[1]] || ""
                                onValueCommitted: (value) => root.workspace.commit(
                                    combatStat.modelData[1], value)
                            }
                        }
                    }
                }
            }
        }
    }
}
