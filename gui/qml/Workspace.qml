pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "." as Design

Item {
    id: root

    required property var controller

    property var enemyData: ({})
    property var ratingNames: []
    property bool schemaEditMode: false
    property var schemaDraft: []
    property var fieldErrors: ({})
    property string toastText: ""
    property bool toastIsError: false
    property string detailedTarget: ""
    property int detailedSkillIndex: -1

    function refreshData(serialized, clearErrors) {
        enemyData = JSON.parse(serialized)
        if (clearErrors !== false)
            fieldErrors = ({})
    }

    function refreshRatingNames(serialized) {
        ratingNames = JSON.parse(serialized)
    }

    function commit(field, value) {
        root.controller.updateProperty(field, JSON.stringify(value))
    }

    function commitAttackType(value) {
        commit("attack_type", value)
        if (value === "近战" || value === "不攻击")
            commit("attack_range_radius", 0)
    }

    function commitSkill(skillIndex, field, value) {
        var skill = JSON.parse(JSON.stringify(enemyData.skills[skillIndex]))
        skill[field] = value
        root.controller.updateSkill(skillIndex, JSON.stringify(skill))
    }

    function showToast(message, isError) {
        toastText = message
        toastIsError = isError
        toastTimer.restart()
    }

    function confirmNewCard(isReset) {
        newCardDialog.dialogTitle = isReset
                ? "恢复默认数据？"
                : "丢弃当前内容并新建？"
        newCardDialog.message = isReset
                ? "当前编辑内容将被默认数据替换，且无法撤销。"
                : "所有未保存的修改都将丢失，且无法撤销。"
        newCardDialog.confirmText = isReset ? "恢复默认" : "丢弃并新建"
        newCardDialog.open()
    }

    function openDetailed(target, title, value, skillIndex) {
        detailedTarget = target
        detailedSkillIndex = skillIndex === undefined ? -1 : skillIndex
        detailedDialog.openFor(title, value)
    }

    function saveDetailed(value) {
        if (detailedTarget === "skillEffect")
            commitSkill(detailedSkillIndex, "效果", value)
        else
            commit(detailedTarget, value)
    }

    Component.onCompleted: {
        refreshData(root.controller.enemyDataJson, true)
        refreshRatingNames(root.controller.ratingNamesJson)
    }

    Connections {
        target: root.controller
        function onEnemyDataChanged(serialized) { root.refreshData(serialized, true) }
        function onRatingNamesChanged(serialized) { root.refreshRatingNames(serialized) }
        function onMessageChanged(message) { root.showToast(message, false) }
        function onFieldError(field, message) {
            var errors = Object.assign({}, root.fieldErrors)
            errors[field] = message
            root.fieldErrors = errors
            root.showToast(message, true)
            root.refreshData(root.controller.enemyDataJson, false)
        }
        function onDialogRequested(title, message, tone) {
            messageDialog.show(title, message, tone)
        }
    }

    Shortcut { sequence: "Ctrl+N"; onActivated: root.confirmNewCard(false) }
    Shortcut { sequence: "Ctrl+O"; onActivated: root.controller.requestOpen() }
    Shortcut { sequence: "Ctrl+S"; onActivated: root.controller.requestSave() }
    Shortcut { sequence: "Ctrl+E"; onActivated: root.controller.requestExport() }
    Shortcut { sequence: "F5"; onActivated: root.controller.requestRefresh() }
    Shortcut { sequence: "Ctrl+Q"; onActivated: root.controller.requestQuit() }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ToolBar {
            Layout.fillWidth: true
            implicitHeight: 52
            padding: Design.Theme.space2

            RowLayout {
                anchors.fill: parent
                spacing: Design.Theme.space2

                AppButton { text: "新建"; iconSource: "icons/new.svg"; onClicked: root.confirmNewCard(false) }
                AppButton { text: "打开"; iconSource: "icons/open.svg"; onClicked: root.controller.requestOpen() }
                AppButton { text: "保存"; iconSource: "icons/save.svg"; onClicked: root.controller.requestSave() }
                AppButton {
                    text: "参考 PRTS"
                    appearance: "secondary"
                    enabled: !root.controller.prtsBusy
                    onClicked: prtsDialog.open()
                }
                AppButton {
                    id: moreButton
                    text: "更多"
                    appearance: "subtle"
                    onClicked: commandMenu.open()

                    Menu {
                        id: commandMenu
                        y: moreButton.height
                        MenuItem { text: "刷新预览\tF5"; onTriggered: root.controller.requestRefresh() }
                        MenuItem { text: "重置数据"; onTriggered: root.confirmNewCard(true) }
                        MenuSeparator {}
                        MenuItem { text: "关于"; onTriggered: root.controller.requestAbout() }
                        MenuItem { text: "退出\tCtrl+Q"; onTriggered: root.controller.requestQuit() }
                    }
                }
                Item { Layout.fillWidth: true }
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            Pane {
                SplitView.preferredWidth: Math.min(520, root.width * 0.38)
                SplitView.minimumWidth: 360
                padding: Design.Theme.space3

                background: Rectangle { color: Design.Theme.surfaceSubtle }

                ColumnLayout {
                    anchors.fill: parent
                    spacing: Design.Theme.space3

                    TabBar {
                        id: editorTabs
                        objectName: "editorTabs"
                        Layout.fillWidth: true
                        currentIndex: 0
                        implicitHeight: 48
                        padding: Design.Theme.space1
                        spacing: Design.Theme.space1

                        background: Rectangle {
                            radius: Design.Theme.radiusMedium
                            color: Design.Theme.tabTrack
                            border.width: 1
                            border.color: Design.Theme.border
                        }

                        AppTabButton {
                            width: (editorTabs.availableWidth - editorTabs.spacing * 4) / 5
                            text: "基础"
                        }
                        AppTabButton {
                            width: (editorTabs.availableWidth - editorTabs.spacing * 4) / 5
                            text: "战斗"
                        }
                        AppTabButton {
                            width: (editorTabs.availableWidth - editorTabs.spacing * 4) / 5
                            text: "抗性"
                        }
                        AppTabButton {
                            width: (editorTabs.availableWidth - editorTabs.spacing * 4) / 5
                            text: "技能"
                        }
                        AppTabButton {
                            width: (editorTabs.availableWidth - editorTabs.spacing * 4) / 5
                            text: "评价"
                        }
                    }

                    StackLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        currentIndex: editorTabs.currentIndex

                        ScrollView {
                            id: basicScroll
                            clip: true
                            contentWidth: availableWidth
                            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                            ColumnLayout {
                                width: basicScroll.availableWidth
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
                                            value: root.enemyData.name || ""
                                            hasError: root.fieldErrors.name !== undefined
                                            errorText: root.fieldErrors.name || ""
                                            onValueCommitted: root.commit("name", value)
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
                                            value: root.enemyData.grade || ""
                                            hasError: root.fieldErrors.grade !== undefined
                                            errorText: root.fieldErrors.grade || ""
                                            onValueCommitted: root.commit("grade", value)
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
                                            value: root.enemyData.attack_type || ""
                                            onValueCommitted: root.commitAttackType(value)
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
                                            value: root.enemyData.damage_type || ""
                                            onValueCommitted: root.commit("damage_type", value)
                                        }
                                        Label { text: "行动方式" }
                                        AppComboBox {
                                            Layout.fillWidth: true
                                            options: [
                                                { value: "地面", label: "地面" },
                                                { value: "飞行", label: "飞行" }
                                            ]
                                            value: root.enemyData.action_type || ""
                                            onValueCommitted: root.commit("action_type", value)
                                        }
                                        Label { text: "地位" }
                                        AppComboBox {
                                            Layout.fillWidth: true
                                            options: [
                                                { value: "普通", label: "普通" },
                                                { value: "精英", label: "精英" },
                                                { value: "领袖", label: "领袖" }
                                            ]
                                            value: root.enemyData.position || ""
                                            onValueCommitted: root.commit("position", value)
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
                                            value: root.enemyData.category || "其他"
                                            onValueCommitted: root.commit("category", value)
                                        }
                                        Label { text: "头像" }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            AppTextField {
                                                Layout.fillWidth: true
                                                value: root.enemyData.avatar_path || ""
                                                hasError: root.fieldErrors.avatar_path !== undefined
                                                errorText: root.fieldErrors.avatar_path || ""
                                                onValueCommitted: root.commit("avatar_path", value)
                                            }
                                            AppButton {
                                                text: "选择"
                                                appearance: "secondary"
                                                onClicked: root.controller.chooseAvatar()
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        ScrollView {
                            id: combatScroll
                            clip: true
                            contentWidth: availableWidth
                            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                            ColumnLayout {
                                width: combatScroll.availableWidth
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
                                                                 || (root.enemyData.attack_type !== "近战"
                                                                     && root.enemyData.attack_type !== "不攻击")
                                                        value: Number(root.enemyData[combatStat.modelData[1]] ?? 0)
                                                        minimum: combatStat.modelData[2]
                                                        maximum: combatStat.modelData[3]
                                                        stepSize: combatStat.modelData[4]
                                                        decimals: combatStat.modelData[5]
                                                        hasError: root.fieldErrors[combatStat.modelData[1]] !== undefined
                                                        errorText: root.fieldErrors[combatStat.modelData[1]] || ""
                                                        onValueCommitted: (value) => root.commit(
                                                            combatStat.modelData[1], value)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        ScrollView {
                            id: resistanceScroll
                            clip: true
                            contentWidth: availableWidth
                            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                            ColumnLayout {
                                width: resistanceScroll.availableWidth
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
                                                checked: (root.enemyData.abnormal_resistances || {})[resistanceBox.modelData] > 0
                                                onToggled: root.controller.updateResistance(
                                                    resistanceBox.modelData, checked ? 1.0 : 0.0)
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        ScrollView {
                            id: skillsScroll
                            clip: true
                            contentWidth: availableWidth
                            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                            ColumnLayout {
                                width: skillsScroll.availableWidth
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
                                            onClicked: root.controller.addSkill()
                                        }
                                    ]
                                    Rectangle {
                                        visible: (root.enemyData.skills || []).length === 0
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
                                        model: root.enemyData.skills || []
                                        delegate: AppSection {
                                            id: skillSection
                                            required property int index
                                            required property var modelData
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
                                                    onClicked: root.controller.removeSkill(skillSection.index)
                                                }
                                            ]
                                            GridLayout {
                                                columns: 2
                                                width: parent.width
                                                Label { text: "名称" }
                                                AppTextField {
                                                    Layout.fillWidth: true
                                                    value: skillSection.modelData["名称"] || ""
                                                    onValueCommitted: (value) => root.commitSkill(
                                                        skillSection.index, "名称", value)
                                                }
                                                Label { text: "冷却时间" }
                                                AppTextField {
                                                    Layout.fillWidth: true
                                                    value: skillSection.modelData["冷却时间"] || ""
                                                    onValueCommitted: (value) => root.commitSkill(
                                                        skillSection.index, "冷却时间", value)
                                                }
                                                Label { text: "技力消耗" }
                                                AppTextField {
                                                    Layout.fillWidth: true
                                                    value: skillSection.modelData["技力消耗"] || ""
                                                    onValueCommitted: (value) => root.commitSkill(
                                                        skillSection.index, "技力消耗", value)
                                                }
                                            }
                                            AppLongTextEditor {
                                                width: parent.width
                                                title: "技能效果"
                                                placeholderText: "描述技能机制、触发条件与效果"
                                                framed: false
                                                editorHeight: 104
                                                value: skillSection.modelData["效果"] || ""
                                                onValueCommitted: (value) => root.commitSkill(
                                                    skillSection.index, "效果", value)
                                                onExpandRequested: root.openDetailed(
                                                    "skillEffect",
                                                    "技能效果",
                                                    skillSection.modelData["效果"] || "",
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
                                    value: root.enemyData.talents_abilities || ""
                                    onValueCommitted: root.commit("talents_abilities", value)
                                    onExpandRequested: root.openDetailed(
                                        "talents_abilities", "天赋与能力", root.enemyData.talents_abilities || ""
                                    )
                                }
                            }
                        }

                        ScrollView {
                            id: ratingScroll
                            clip: true
                            contentWidth: availableWidth
                            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                            ColumnLayout {
                                width: ratingScroll.availableWidth
                                spacing: Design.Theme.space3
                                AppSection {
                                    title: "评价维度"
                                    Layout.fillWidth: true
                                    headerActions: [
                                        AppIconButton {
                                            visible: !root.schemaEditMode
                                            width: 40
                                            height: 40
                                            icon.source: "icons/sliders.svg"
                                            icon.width: 24
                                            icon.height: 24
                                            display: AbstractButton.IconOnly
                                            toolTipText: "编辑标准"
                                            onClicked: {
                                                root.schemaDraft = root.ratingNames.slice()
                                                root.schemaEditMode = true
                                            }
                                        },
                                        AppButton {
                                            visible: root.schemaEditMode
                                            width: 40
                                            height: 40
                                            text: ""
                                            iconSource: "icons/save.svg"
                                            ToolTip.visible: hovered
                                            ToolTip.text: "保存标准"
                                            onClicked: {
                                                root.controller.updateRatingSchema(
                                                    JSON.stringify(root.schemaDraft))
                                                root.schemaEditMode = false
                                            }
                                        },
                                        AppButton {
                                            visible: root.schemaEditMode
                                            text: "取消"
                                            appearance: "subtle"
                                            onClicked: {
                                                root.schemaDraft = root.ratingNames.slice()
                                                root.schemaEditMode = false
                                            }
                                        }
                                    ]
                                    Repeater {
                                        model: root.schemaEditMode ? root.schemaDraft : root.ratingNames
                                        delegate: RowLayout {
                                            id: ratingRow
                                            required property int index
                                            required property string modelData
                                            width: parent.width
                                            spacing: Design.Theme.space2
                                            AppTextField {
                                                visible: root.schemaEditMode
                                                Layout.fillWidth: root.schemaEditMode
                                                value: ratingRow.modelData
                                                maximumLength: 8
                                                onEditingFinished: {
                                                    var values = root.schemaDraft.slice()
                                                    values[ratingRow.index] = text.trim()
                                                    root.schemaDraft = values
                                                }
                                            }
                                            Label {
                                                visible: !root.schemaEditMode
                                                text: ratingRow.modelData
                                                Layout.preferredWidth: 100
                                            }
                                            RatingStars {
                                                visible: !root.schemaEditMode
                                                dimensionName: ratingRow.modelData
                                                score: (root.enemyData.rating_scores || [])[ratingRow.index] || 1
                                                onScoreSelected: (score) => root.controller.updateRatingScore(
                                                    ratingRow.index, score)
                                            }
                                            AppIconButton {
                                                visible: root.schemaEditMode
                                                Layout.preferredWidth: 40
                                                Layout.preferredHeight: 40
                                                icon.source: "icons/delete.svg"
                                                icon.width: 24
                                                icon.height: 24
                                                display: AbstractButton.IconOnly
                                                toolTipText: "删除评价维度"
                                                enabled: root.schemaDraft.length > 0
                                                onClicked: {
                                                    var values = root.schemaDraft.slice()
                                                    values.splice(ratingRow.index, 1)
                                                    root.schemaDraft = values
                                                }
                                            }
                                        }
                                    }
                                    AppButton {
                                        readonly property bool atLimit: root.schemaDraft.length >= 5

                                        visible: root.schemaEditMode
                                        width: parent.width
                                        text: atLimit ? "" : "+ 添加维度"
                                        iconSource: atLimit ? "icons/ban.svg" : ""
                                        appearance: "subtle"
                                        enabled: !atLimit
                                        ToolTip.visible: atLimit && hovered
                                        ToolTip.text: "已达上限（最多 5 项）"
                                        onClicked: root.schemaDraft = root.schemaDraft.concat(["新维度"])
                                    }
                                    Label {
                                        visible: !root.schemaEditMode && root.ratingNames.length === 0
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
                                    value: root.enemyData.brief_description || ""
                                    onValueCommitted: root.commit("brief_description", value)
                                    onExpandRequested: root.openDetailed(
                                        "brief_description", "敌人描述", root.enemyData.brief_description || ""
                                    )
                                }
                                AppLongTextEditor {
                                    title: "简要评价"
                                    Layout.fillWidth: true
                                    placeholderText: "输入简要评价"
                                    editorHeight: 116
                                    value: root.enemyData.brief_comment || ""
                                    onValueCommitted: root.commit("brief_comment", value)
                                    onExpandRequested: root.openDetailed(
                                        "brief_comment", "简要评价", root.enemyData.brief_comment || ""
                                    )
                                }
                            }
                        }
                    }
                }
            }

            Pane {
                SplitView.fillWidth: true
                padding: Design.Theme.space4
                background: Rectangle { color: Design.Theme.surfaceCanvas }

                PreviewViewport {
                    anchors.fill: parent
                    source: "image://enemy-card/current?revision="
                            + root.controller.previewRevision
                    busy: root.controller.busy
                    onExportRequested: root.controller.requestExport()
                }
            }
        }
    }

    Rectangle {
        id: toast
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: Design.Theme.space5
        anchors.topMargin: 64
        visible: opacity > 0
        opacity: toastTimer.running ? 1 : 0
        width: Math.min(parent.width - 40, toastContent.implicitWidth + 32)
        height: Math.max(44, toastContent.implicitHeight + 20)
        radius: Design.Theme.radiusMedium
        color: Design.Theme.surface
        border.width: 1
        border.color: Design.Theme.border
        z: 20

        Behavior on opacity {
            NumberAnimation {
                duration: toastTimer.running ? 160 : 100
                easing.type: toastTimer.running ? Easing.OutCubic : Easing.InCubic
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 4
            radius: 2
            color: root.toastIsError ? Design.Theme.danger : Design.Theme.success
        }

        Row {
            id: toastContent
            anchors.centerIn: parent
            spacing: Design.Theme.space2

            Rectangle {
                width: 20
                height: 20
                radius: 10
                color: root.toastIsError
                       ? Design.Theme.dangerSubtle : Design.Theme.successSubtle

                Label {
                    anchors.centerIn: parent
                    text: root.toastIsError ? "!" : "✓"
                    color: root.toastIsError ? Design.Theme.danger : Design.Theme.success
                    font.pixelSize: 12
                    font.weight: Font.Bold
                }
            }

            Label {
                id: toastLabel
                width: Math.min(implicitWidth, root.width - 100)
                wrapMode: Text.Wrap
                text: root.toastText
                color: Design.Theme.textPrimary
            }
        }
    }
    Timer {
        id: toastTimer
        interval: 4000
        repeat: false
    }

    DetailedTextDialog {
        id: detailedDialog
        onSaved: (value) => root.saveDetailed(value)
    }

    AppMessageDialog {
        id: messageDialog
    }

    AppMessageDialog {
        id: newCardDialog
        tone: "question"
        showCancel: true
        destructive: true
        onConfirmed: root.controller.requestNew()
    }

    Dialog {
        id: prtsDialog

        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(parent ? parent.width - 48 : 440, 440)
        modal: true
        title: ""
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape
        padding: Design.Theme.space5
        onAccepted: root.controller.requestPrtsQuery(prtsName.text)
        onOpened: prtsName.focusInput(true)

        Overlay.modal: Rectangle {
            color: Design.Theme.overlay
        }

        background: Rectangle {
            color: Design.Theme.surface
            radius: Design.Theme.radiusLarge
            border.width: 1
            border.color: Design.Theme.border
        }

        contentItem: ColumnLayout {
            spacing: Design.Theme.space4

            Label {
                text: "参考 PRTS"
                color: Design.Theme.textPrimary
                font.family: Design.Theme.fontFamily
                font.pixelSize: 18
                font.weight: Font.DemiBold
            }

            Label {
                Layout.fillWidth: true
                text: "输入敌人名称，自动填入相关字段。"
                color: Design.Theme.textSecondary
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.bodyFontSize
            }

            AppTextField {
                id: prtsName
                Layout.fillWidth: true
                placeholderText: "敌人名称"
                showFocusFrame: false
                onAccepted: {
                    if (fetchPrtsButton.enabled)
                        prtsDialog.accept()
                }
            }

            BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                running: root.controller.prtsBusy
                visible: running
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Design.Theme.space2

                Item { Layout.fillWidth: true }

                AppButton {
                    text: "取消"
                    appearance: "secondary"
                    onClicked: prtsDialog.reject()
                }

                AppButton {
                    id: fetchPrtsButton
                    text: "获取数据"
                    enabled: prtsName.text.trim().length > 0 && !root.controller.prtsBusy
                    onClicked: prtsDialog.accept()
                }
            }
        }
    }
}
