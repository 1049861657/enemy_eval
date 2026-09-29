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
            title: "评价维度"
            Layout.fillWidth: true
            titleTrailing: [
                RatingDisplaySwitch {
                    visible: !root.workspace.schemaEditMode
                    radarOn: root.workspace.controller.ratingRadar
                    onModePicked: (radar) => root.workspace.controller.setRatingRadar(radar)
                }
            ]
            headerActions: [
                AppIconButton {
                    visible: !root.workspace.schemaEditMode
                    width: 40
                    height: 40
                    icon.source: "icons/sliders.svg"
                    icon.width: 24
                    icon.height: 24
                    display: AbstractButton.IconOnly
                    toolTipText: "编辑标准"
                    onClicked: {
                        root.workspace.schemaDraft = root.workspace.ratingNames.slice()
                        root.workspace.schemaEditMode = true
                    }
                },
                AppButton {
                    visible: root.workspace.schemaEditMode
                    width: 40
                    height: 40
                    text: ""
                    iconSource: "icons/save.svg"
                    ToolTip.visible: hovered
                    ToolTip.text: "保存标准"
                    onClicked: {
                        root.workspace.controller.updateRatingSchema(
                            JSON.stringify(root.workspace.schemaDraft))
                        root.workspace.schemaEditMode = false
                    }
                },
                AppButton {
                    visible: root.workspace.schemaEditMode
                    text: "取消"
                    appearance: "subtle"
                    onClicked: {
                        root.workspace.schemaDraft = root.workspace.ratingNames.slice()
                        root.workspace.schemaEditMode = false
                    }
                }
            ]
            Repeater {
                model: root.workspace.schemaEditMode
                        ? root.workspace.schemaDraft : root.workspace.ratingNames
                delegate: RowLayout {
                    id: ratingRow
                    required property int index
                    required property string modelData
                    width: parent.width
                    spacing: Design.Theme.space2
                    AppTextField {
                        visible: root.workspace.schemaEditMode
                        Layout.fillWidth: root.workspace.schemaEditMode
                        value: ratingRow.modelData
                        maximumLength: 8
                        onEditingFinished: {
                            var values = root.workspace.schemaDraft.slice()
                            values[ratingRow.index] = text.trim()
                            root.workspace.schemaDraft = values
                        }
                    }
                    Label {
                        visible: !root.workspace.schemaEditMode
                        text: ratingRow.modelData
                        Layout.preferredWidth: 100
                    }
                    RatingStars {
                        visible: !root.workspace.schemaEditMode
                        dimensionName: ratingRow.modelData
                        score: {
                            var scores = root.workspace.enemyData.rating_scores || []
                            return scores[ratingRow.index] !== undefined
                                   ? scores[ratingRow.index]
                                   : root.workspace.controller.defaultRatingScore
                        }
                        onScoreSelected: (score) => root.workspace.controller.updateRatingScore(
                            ratingRow.index, score)
                    }
                    AppIconButton {
                        visible: root.workspace.schemaEditMode
                        Layout.preferredWidth: 40
                        Layout.preferredHeight: 40
                        icon.source: "icons/delete.svg"
                        icon.width: 24
                        icon.height: 24
                        display: AbstractButton.IconOnly
                        toolTipText: "删除评价维度"
                        enabled: root.workspace.schemaDraft.length > 0
                        onClicked: {
                            var values = root.workspace.schemaDraft.slice()
                            values.splice(ratingRow.index, 1)
                            root.workspace.schemaDraft = values
                        }
                    }
                }
            }
            AppButton {
                readonly property bool atLimit: root.workspace.schemaDraft.length >= 5

                visible: root.workspace.schemaEditMode
                width: parent.width
                text: atLimit ? "" : "+ 添加维度"
                iconSource: atLimit ? "icons/ban.svg" : ""
                appearance: "subtle"
                enabled: !atLimit
                ToolTip.visible: atLimit && hovered
                ToolTip.text: "已达上限（最多 5 项）"
                onClicked: root.workspace.schemaDraft = root.workspace.schemaDraft.concat(["新维度"])
            }
            Label {
                visible: !root.workspace.schemaEditMode && root.workspace.ratingNames.length === 0
                width: parent.width
                text: "暂无评价维度"
                horizontalAlignment: Text.AlignHCenter
                color: Design.Theme.textSecondary
            }
        }
        AppLongTextEditor {
            title: "敌人描述"
            Layout.fillWidth: true
            placeholderText: "输入敌人的背景、外观或行为特征"
            editorHeight: 116
            value: root.workspace.enemyData.brief_description || ""
            onValueCommitted: root.workspace.commit("brief_description", value)
            onExpandRequested: root.workspace.openDetailed(
                "brief_description", "敌人描述", root.workspace.enemyData.brief_description || ""
            )
        }
        AppLongTextEditor {
            title: "简要评价"
            Layout.fillWidth: true
            placeholderText: "输入简要评价"
            editorHeight: 116
            value: root.workspace.enemyData.brief_comment || ""
            onValueCommitted: root.workspace.commit("brief_comment", value)
            onExpandRequested: root.workspace.openDetailed(
                "brief_comment", "简要评价", root.workspace.enemyData.brief_comment || ""
            )
        }
    }
}
