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
            title: "基本信息"
            Layout.fillWidth: true
            GridLayout {
                columns: 2
                width: parent.width
                columnSpacing: Design.Theme.space3
                rowSpacing: Design.Theme.space2
                Label { text: "敌人名称" }
                AppTextField {
                    Layout.fillWidth: true
                    value: root.workspace.enemyData.name || ""
                    hasError: root.workspace.fieldErrors.name !== undefined
                    errorText: root.workspace.fieldErrors.name || ""
                    onValueCommitted: root.workspace.commit("name", value)
                }
                Label { text: "等级" }
                AppComboBox {
                    Layout.fillWidth: true
                    options: [
                        { value: "S", label: "S" },
                        { value: "A", label: "A" },
                        { value: "B", label: "B" },
                        { value: "C", label: "C" },
                        { value: "D", label: "D" }
                    ]
                    value: root.workspace.enemyData.grade || ""
                    hasError: root.workspace.fieldErrors.grade !== undefined
                    errorText: root.workspace.fieldErrors.grade || ""
                    onValueCommitted: root.workspace.commit("grade", value)
                }
                Label { text: "攻击方式" }
                AppComboBox {
                    Layout.fillWidth: true
                    options: [
                        { value: "近战", label: "近战" },
                        { value: "远程", label: "远程" },
                        { value: "近战/远程", label: "近战/远程" },
                        { value: "不攻击", label: "不攻击" }
                    ]
                    value: root.workspace.enemyData.attack_type || ""
                    onValueCommitted: root.workspace.commitAttackType(value)
                }
                Label { text: "伤害类型" }
                AppComboBox {
                    Layout.fillWidth: true
                    options: [
                        { value: "物理", label: "物理" },
                        { value: "法术", label: "法术" },
                        { value: "治疗", label: "治疗" },
                        { value: "无", label: "无" }
                    ]
                    value: root.workspace.enemyData.damage_type || ""
                    onValueCommitted: root.workspace.commit("damage_type", value)
                }
                Label { text: "行动方式" }
                AppComboBox {
                    Layout.fillWidth: true
                    options: [
                        { value: "地面", label: "地面" },
                        { value: "飞行", label: "飞行" }
                    ]
                    value: root.workspace.enemyData.action_type || ""
                    onValueCommitted: root.workspace.commit("action_type", value)
                }
                Label { text: "地位" }
                AppComboBox {
                    Layout.fillWidth: true
                    options: [
                        { value: "普通", label: "普通" },
                        { value: "精英", label: "精英" },
                        { value: "领袖", label: "领袖" }
                    ]
                    value: root.workspace.enemyData.position || ""
                    onValueCommitted: root.workspace.commit("position", value)
                }
                Label { text: "种类" }
                AppComboBox {
                    Layout.fillWidth: true
                    options: [
                        { value: "感染生物", label: "感染生物" },
                        { value: "无人机", label: "无人机" },
                        { value: "萨卡兹", label: "萨卡兹" },
                        { value: "宿主", label: "宿主" },
                        { value: "海怪", label: "海怪" },
                        { value: "法术造物", label: "法术造物" },
                        { value: "源石造物", label: "源石造物" },
                        { value: "化物", label: "化物" },
                        { value: "机械", label: "机械" },
                        { value: "野生动物", label: "野生动物" },
                        { value: "坍缩体", label: "坍缩体" },
                        { value: "其他", label: "其他" }
                    ]
                    value: root.workspace.enemyData.category || "其他"
                    onValueCommitted: root.workspace.commit("category", value)
                }
                Label { text: "头像" }
                RowLayout {
                    Layout.fillWidth: true
                    AppTextField {
                        Layout.fillWidth: true
                        value: root.workspace.enemyData.avatar_path || ""
                        hasError: root.workspace.fieldErrors.avatar_path !== undefined
                        errorText: root.workspace.fieldErrors.avatar_path || ""
                        onValueCommitted: root.workspace.commit("avatar_path", value)
                    }
                    AppButton {
                        text: "选择"
                        appearance: "secondary"
                        onClicked: root.workspace.controller.chooseAvatar()
                    }
                }
            }
        }
    }
}
