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
            title: "技能设定"
            Layout.fillWidth: true
            headerActions: [
                AppIconButton {
                    width: 40
                    height: 40
                    icon.source: "icons/add.svg"
                    icon.width: 24
                    icon.height: 24
                    display: AbstractButton.IconOnly
                    toolTipText: "添加技能"
                    onClicked: root.workspace.controller.skills.add()
                }
            ]
            Rectangle {
                visible: root.workspace.controller.skills.count === 0
                width: parent.width
                implicitHeight: 84
                radius: Design.Theme.radiusMedium
                color: Design.Theme.surfaceSubtle
                border.width: 1
                border.color: Design.Theme.border

                Label {
                    anchors.centerIn: parent
                    text: "暂无技能"
                    color: Design.Theme.textSecondary
                    font.family: Design.Theme.fontFamily
                }
            }
            Repeater {
                model: root.workspace.controller.skills
                delegate: AppSection {
                    id: skillSection
                    required property int index
                    required property string skillName
                    required property string cooldown
                    required property string cost
                    required property string effect
                    width: parent.width
                    title: "技能 " + (skillSection.index + 1)
                    headerActions: [
                        AppIconButton {
                            width: 40
                            height: 40
                            icon.source: "icons/delete.svg"
                            icon.width: 24
                            icon.height: 24
                            display: AbstractButton.IconOnly
                            toolTipText: "删除技能 " + (skillSection.index + 1)
                            onClicked: root.workspace.controller.skills.remove(skillSection.index)
                        }
                    ]
                    GridLayout {
                        columns: 2
                        width: parent.width
                        Label { text: "名称" }
                        AppTextField {
                            Layout.fillWidth: true
                            value: skillSection.skillName
                            onValueCommitted: (value) => root.workspace.controller.skills.updateField(
                                skillSection.index, "名称", value)
                        }
                        Label { text: "冷却时间" }
                        AppTextField {
                            Layout.fillWidth: true
                            value: skillSection.cooldown
                            onValueCommitted: (value) => root.workspace.controller.skills.updateField(
                                skillSection.index, "冷却时间", value)
                        }
                        Label { text: "技力消耗" }
                        AppTextField {
                            Layout.fillWidth: true
                            value: skillSection.cost
                            onValueCommitted: (value) => root.workspace.controller.skills.updateField(
                                skillSection.index, "技力消耗", value)
                        }
                    }
                    AppLongTextEditor {
                        width: parent.width
                        title: "技能效果"
                        placeholderText: "描述技能机制、触发条件与效果"
                        framed: false
                        editorHeight: 104
                        value: skillSection.effect
                        onValueCommitted: (value) => root.workspace.controller.skills.updateField(
                            skillSection.index, "效果", value)
                        onExpandRequested: root.workspace.openDetailed(
                            "skillEffect",
                            "技能效果",
                            skillSection.effect,
                            skillSection.index
                        )
                    }
                }
            }
        }
        AppLongTextEditor {
            title: "天赋与能力"
            Layout.fillWidth: true
            placeholderText: "输入天赋与能力描述"
            editorHeight: 128
            value: root.workspace.enemyData.talents_abilities || ""
            onValueCommitted: root.workspace.commit("talents_abilities", value)
            onExpandRequested: root.workspace.openDetailed(
                "talents_abilities", "天赋与能力", root.workspace.enemyData.talents_abilities || ""
            )
        }
    }
}
