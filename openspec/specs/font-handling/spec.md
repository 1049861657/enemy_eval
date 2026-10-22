# font-handling Specification

## Purpose

让界面与卡片渲染在不同 Windows 机器上都能使用可用、确定的中文字体，避免缺字方框与跨机器输出差异。

## Requirements

### Requirement: 卡片使用随包字体

卡片渲染 SHALL 始终使用随包提供的 HarmonyOS Sans SC Regular，不得依赖操作系统是否安装中文字体；随包字体文件缺失或损坏时，系统 SHALL 回退到系统中文字体并记录告警，不得中断渲染。

#### Scenario: 系统没有中文字体

- **WHEN** 目标机器未安装任何中文字体
- **THEN** 卡片仍使用随包字体正常渲染中文

#### Scenario: 随包字体缺失

- **WHEN** 随包字体文件不存在或无法解析
- **THEN** 按字体族回退到系统字体，并记录一条告警

### Requirement: 界面字体回退栈

界面文本 SHALL 按声明顺序使用字体族回退栈：Microsoft YaHei UI、Microsoft YaHei、Segoe UI、HarmonyOS Sans SC；随包字体 SHALL 注册给界面框架，使前三个族不可用时仍能显示中文。

#### Scenario: 非中文 Windows

- **WHEN** 系统没有 Microsoft YaHei 系列字体
- **THEN** 界面继续使用后续字体，中文不显示为方框

#### Scenario: 系统字体齐全

- **WHEN** 系统安装了 Microsoft YaHei UI
- **THEN** 界面优先使用该系统字体

### Requirement: 移除硬编码字体路径

字体解析 SHALL NOT 依赖固定的 `C:/Windows/Fonts/*` 路径；卡片字体只从随包资源加载，系统字体仅作为随包资源不可用时的回退。

#### Scenario: 系统字体目录不同

- **WHEN** Windows 安装目录或字体目录不在默认位置
- **THEN** 卡片字体仍能从随包资源加载

### Requirement: 输出确定性

同一版本的应用 SHALL 对同一份数据使用同一字体与字号进行卡片测量和绘制，输出不受目标机器系统字体影响。

#### Scenario: 跨机器一致性

- **WHEN** 两台机器分别有和没有系统中文字体
- **THEN** 同一配置生成的卡片文字宽度、换行与高度一致

### Requirement: 字体分发与许可

打包产物 SHALL 同时包含随包字体文件与 HarmonyOS Sans 字体许可文本；软件界面 SHALL 显著声明使用了 HarmonyOS Sans；构建校验 SHALL 在缺少字体或许可证时失败。

#### Scenario: 产物缺少字体

- **WHEN** 打包产物中缺少字体或许可证
- **THEN** 构建校验失败并指出缺失项

#### Scenario: 软件内字体声明

- **WHEN** 用户查看关于信息
- **THEN** 可以看到使用了 HarmonyOS Sans 的声明
