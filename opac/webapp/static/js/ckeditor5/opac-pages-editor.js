/**
 * CKEditor 5 Classic init for OPAC admin Pages (add/edit).
 * Loads all open-source features from the UMD bundle (GPL).
 * Expects global CKEDITOR from ckeditor5.umd.js and optional CKEDITOR_TRANSLATIONS.
 *
 * Excluded (break HTML pages or need external services/config):
 * Markdown, Title, CloudServices, CKBox, CKFinder, EasyImage,
 * SimpleUploadAdapter, Mention, Autosave, Minimap, BalloonToolbar, BlockToolbar.
 */
(function () {
    "use strict";

    var C = window.CKEDITOR;
    if (!C || !C.ClassicEditor) {
        console.error("CKEditor 5 UMD bundle not loaded");
        return;
    }

    var element = document.querySelector("#content");
    if (!element) {
        return;
    }

    // Prefer admin session locale (set by _ckeditor5.html); fall back to pt-br / en.
    var language = window.OPAC_CKEDITOR_LANG || "pt-br";
    if (
        language !== "en" &&
        !(window.CKEDITOR_TRANSLATIONS && window.CKEDITOR_TRANSLATIONS[language])
    ) {
        language = "en";
    }

    var plugins = [
        C.Essentials,
        C.Paragraph,
        C.Heading,
        C.Bold,
        C.Italic,
        C.Underline,
        C.Strikethrough,
        C.Code,
        C.Subscript,
        C.Superscript,
        C.RemoveFormat,
        C.Font,
        C.Highlight,
        C.Alignment,
        C.List,
        C.ListProperties,
        C.TodoList,
        C.AdjacentListsSupport,
        C.Indent,
        C.IndentBlock,
        C.Link,
        C.AutoLink,
        C.Bookmark,
        C.BlockQuote,
        C.CodeBlock,
        C.HorizontalLine,
        C.PageBreak,
        C.Table,
        C.TableToolbar,
        C.TableProperties,
        C.TableCellProperties,
        C.TableCaption,
        C.TableColumnResize,
        C.Image,
        C.ImageToolbar,
        C.ImageCaption,
        C.ImageStyle,
        C.ImageResize,
        C.ImageInsert,
        C.ImageInsertViaUrl,
        C.ImageUpload,
        C.LinkImage,
        C.PictureEditing,
        C.AutoImage,
        C.Base64UploadAdapter,
        C.MediaEmbed,
        C.MediaEmbedToolbar,
        C.AutoMediaEmbed,
        C.HtmlEmbed,
        C.SpecialCharacters,
        C.SpecialCharactersEssentials,
        C.SpecialCharactersArrows,
        C.SpecialCharactersCurrency,
        C.SpecialCharactersLatin,
        C.SpecialCharactersMathematical,
        C.SpecialCharactersText,
        C.Emoji,
        C.EmojiMention,
        C.EmojiPicker,
        C.Style,
        C.ShowBlocks,
        C.SelectAll,
        C.FindAndReplace,
        C.Fullscreen,
        C.SourceEditing,
        C.GeneralHtmlSupport,
        C.HtmlComment,
        C.EmptyBlock,
        C.TextPartLanguage,
        C.WordCount,
        C.AccessibilityHelp,
        C.Autoformat,
        C.PasteFromOffice,
        C.TextTransformation,
        C.Undo,
    ].filter(Boolean);

    C.ClassicEditor.create(element, {
        licenseKey: "GPL",
        plugins: plugins,
        toolbar: {
            items: [
                "undo",
                "redo",
                "|",
                "heading",
                "style",
                "|",
                "bold",
                "italic",
                "underline",
                "strikethrough",
                "subscript",
                "superscript",
                "code",
                "removeFormat",
                "|",
                "fontSize",
                "fontFamily",
                "fontColor",
                "fontBackgroundColor",
                "highlight",
                "|",
                "alignment",
                "|",
                "bulletedList",
                "numberedList",
                "todoList",
                "outdent",
                "indent",
                "|",
                "link",
                "bookmark",
                "insertImage",
                "mediaEmbed",
                "insertTable",
                "blockQuote",
                "codeBlock",
                "htmlEmbed",
                "horizontalLine",
                "pageBreak",
                "specialCharacters",
                "emoji",
                "|",
                "textPartLanguage",
                "|",
                "findAndReplace",
                "selectAll",
                "showBlocks",
                "sourceEditing",
                "fullscreen",
                "|",
                "accessibilityHelp",
            ],
            shouldNotGroupWhenFull: true,
        },
        menuBar: {
            isVisible: true,
        },
        heading: {
            options: [
                {
                    model: "paragraph",
                    title: "Paragraph",
                    class: "ck-heading_paragraph",
                },
                {
                    model: "heading1",
                    view: "h1",
                    title: "Heading 1",
                    class: "ck-heading_heading1",
                },
                {
                    model: "heading2",
                    view: "h2",
                    title: "Heading 2",
                    class: "ck-heading_heading2",
                },
                {
                    model: "heading3",
                    view: "h3",
                    title: "Heading 3",
                    class: "ck-heading_heading3",
                },
                {
                    model: "heading4",
                    view: "h4",
                    title: "Heading 4",
                    class: "ck-heading_heading4",
                },
                {
                    model: "heading5",
                    view: "h5",
                    title: "Heading 5",
                    class: "ck-heading_heading5",
                },
                {
                    model: "heading6",
                    view: "h6",
                    title: "Heading 6",
                    class: "ck-heading_heading6",
                },
            ],
        },
        alignment: {
            options: ["left", "center", "right", "justify"],
        },
        style: {
            definitions: [
                {
                    name: "Article category",
                    element: "h3",
                    classes: ["category"],
                },
                {
                    name: "Title",
                    element: "h2",
                    classes: ["document-title"],
                },
                {
                    name: "Subtitle",
                    element: "h3",
                    classes: ["document-subtitle"],
                },
                {
                    name: "Info box",
                    element: "p",
                    classes: ["info-box"],
                },
                {
                    name: "Side quote",
                    element: "blockquote",
                    classes: ["side-quote"],
                },
                {
                    name: "Marker",
                    element: "span",
                    classes: ["marker"],
                },
                {
                    name: "Spoiler",
                    element: "span",
                    classes: ["spoiler"],
                },
            ],
        },
        image: {
            toolbar: [
                "imageTextAlternative",
                "toggleImageCaption",
                "|",
                "imageStyle:inline",
                "imageStyle:block",
                "imageStyle:side",
                "imageStyle:alignLeft",
                "imageStyle:alignCenter",
                "imageStyle:alignRight",
                "|",
                "resizeImage",
                "|",
                "linkImage",
            ],
        },
        table: {
            contentToolbar: [
                "tableColumn",
                "tableRow",
                "mergeTableCells",
                "tableProperties",
                "tableCellProperties",
                "toggleTableCaption",
            ],
        },
        list: {
            properties: {
                styles: true,
                startIndex: true,
                reversed: true,
            },
        },
        codeBlock: {
            languages: [
                { language: "plaintext", label: "Plain text" },
                { language: "html", label: "HTML" },
                { language: "css", label: "CSS" },
                { language: "javascript", label: "JavaScript" },
                { language: "python", label: "Python" },
                { language: "xml", label: "XML" },
            ],
        },
        htmlEmbed: {
            showPreviews: true,
        },
        mediaEmbed: {
            previewsInData: true,
        },
        language: {
            ui: language,
            content: language,
            textPartLanguage: [
                { title: "Português", languageCode: "pt" },
                { title: "English", languageCode: "en" },
                { title: "Español", languageCode: "es" },
            ],
        },
        wordCount: {
            onUpdate: function (stats) {
                window.opacPagesEditorWordCount = stats;
            },
        },
        // Preserve legacy CKEditor 4 HTML (previously allowedContent: true).
        htmlSupport: {
            allow: [
                {
                    name: /.*/,
                    attributes: true,
                    classes: true,
                    styles: true,
                },
            ],
        },
    })
        .then(function (editor) {
            window.opacPagesEditor = editor;
            var editable = editor.ui.view.editable.element;
            if (editable) {
                editable.style.minHeight = "500px";
            }
        })
        .catch(function (error) {
            console.error("CKEditor 5 init failed", error);
        });
})();
