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
                    onClicked: root.workspace.beginSchemaEdit()
                },
                AppButton {
                    visible: root.workspace.schemaEditMode
                    text: "完成"
                    onClicked: {
                        if (root.workspace.controller.updateRatingSchema(
                                JSON.stringify(root.workspace.schemaDraft),
                                root.workspace.schemaSaveAsTemplate))
                            root.workspace.schemaEditMode = false
                    }
                },
                AppButton {
                    visible: root.workspace.schemaEditMode
                    text: "取消"
                    appearance: "subtle"
                    onClicked: root.workspace.schemaEditMode = false
                }
            ]
            Repeater {
                model: root.workspace.schemaEditMode
                        ? root.workspace.schemaDraft
                        : (root.workspace.enemyData.ratings || [])
                delegate: RowLayout {
                    id: ratingRow
                    required property int index
                    required property var modelData
                    readonly property string rowName: String(ratingRow.modelData.name || "")
                    width: parent.width
                    spacing: Design.Theme.space2
                    AppTextField {
                        visible: root.workspace.schemaEditMode
                        Layout.fillWidth: root.workspace.schemaEditMode
                        value: ratingRow.rowName
                        maximumLength: 8
                        onEditingFinished: {
                            var values = root.workspace.schemaDraft.slice()
                            var row = values[ratingRow.index]
                            values[ratingRow.index] = { id: row.id, name: text.trim() }
                            root.workspace.schemaDraft = values
                        }
                    }
                    Label {
                        visible: !root.workspace.schemaEditMode
                        text: ratingRow.rowName
                        Layout.preferredWidth: 100
                    }
                    RatingStars {
                        visible: !root.workspace.schemaEditMode
                        dimensionName: ratingRow.rowName
                        score: {
                            var item = (root.workspace.enemyData.ratings || [])[ratingRow.index]
                            return item && item.score !== undefined
                                   ? item.score
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
                onClicked: {
                    var serial = root.workspace.schemaNewSerial + 1
                    root.workspace.schemaNewSerial = serial
                    root.workspace.schemaDraft = root.workspace.schemaDraft.concat(
                        [{ id: "n" + serial, name: "新维度" }])
                }
            }
            Column {
                visible: root.workspace.schemaEditMode
                width: parent.width
                spacing: Design.Theme.space1

                ButtonGroup {
                    id: scopeGroup
                }

                RadioButton {
                    id: cardScope
                    text: "仅此卡"
                    checked: true
                    ButtonGroup.group: scopeGroup
                    font.family: Design.Theme.fontFamily
                    font.pixelSize: Design.Theme.bodyFontSize
                    palette.windowText: Design.Theme.textPrimary
                    palette.highlight: Design.Theme.accent
                    onClicked: root.workspace.schemaSaveAsTemplate = false
                }
                RadioButton {
                    id: templateScope
                    text: "设为全局模板"
                    ButtonGroup.group: scopeGroup
                    font.family: Design.Theme.fontFamily
                    font.pixelSize: Design.Theme.bodyFontSize
                    palette.windowText: Design.Theme.textPrimary
                    palette.highlight: Design.Theme.accent
                    onClicked: root.workspace.schemaSaveAsTemplate = true
                }
                Label {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: root.workspace.schemaSaveAsTemplate
                          ? "作用于此卡及未来的卡"
                          : "保存此卡后写入"
                    color: Design.Theme.textSecondary
                    font.family: Design.Theme.fontFamily
                    font.pixelSize: Design.Theme.captionFontSize
                }

                Connections {
                    target: root.workspace
                    function onSchemaEditModeChanged() {
                        if (root.workspace.schemaEditMode)
                            cardScope.checked = true
                    }
                }
            }
            Label {
                visible: !root.workspace.schemaEditMode
                        && (root.workspace.enemyData.ratings || []).length === 0
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
