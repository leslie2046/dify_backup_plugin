from collections.abc import Generator
from typing import Any
import logging
import zipfile
import io
import re

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.config.logger_format import plugin_logger_handler
from provider.dify_backup import DifyClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)

# MIME type → file extension mapping
MIME_EXT_MAP = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/html": ".html",
    "text/csv": ".csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/json": ".json",
    "application/xml": ".xml",
    "text/xml": ".xml",
}


def _safe_name(name: str) -> str:
    """将名称转换为文件系统安全的字符串，保留中文"""
    safe = (
        "".join(
            c
            for c in name
            if c.isalnum() or c in (" ", "-", "_", ".") or "\u4e00" <= c <= "\u9fff"
        )
        .strip()
        .replace(" ", "_")
    )
    return safe or "unknown"


def _ext_from_mime(mime: str, original_name: str = "") -> str:
    """根据 MIME 或原始文件名推断扩展名"""
    # 先从原始文件名取扩展名
    if original_name and "." in original_name:
        ext = "." + original_name.rsplit(".", 1)[-1].lower()
        if len(ext) <= 6:
            return ext
    # 再从 MIME 取
    base_mime = mime.split(";")[0].strip().lower() if mime else ""
    return MIME_EXT_MAP.get(base_mime, ".bin")


def _build_zip_entry_name(original_name: str, mime: str = "") -> str:
    """生成 ZIP 内文件名，避免重复拼接扩展名。"""
    safe_name = _safe_name(original_name)
    ext = _ext_from_mime(mime, original_name)

    if safe_name.lower().endswith(ext.lower()):
        return safe_name

    if "." in safe_name:
        safe_name = safe_name.rsplit(".", 1)[0]

    return f"{safe_name}{ext}"


class ExportDatasetsTool(Tool):
    """
    Tool for exporting Dify knowledge base (dataset) files as ZIP archives.
    Supports multi-select datasets; defaults to all datasets.
    """

    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        Export selected datasets as ZIP files and return a file list summary.
        """
        dataset_ids_raw = tool_parameters.get("dataset_ids", "").strip()

        base_url = self.runtime.credentials.get("dify_base_url", "")
        email = self.runtime.credentials.get("email", "")
        password = self.runtime.credentials.get("password", "")

        if not base_url or not email or not password:
            yield self.create_text_message("Error: Provider credentials not configured")
            return

        try:
            client = DifyClient(base_url, email, password)

            # ── 1. 确定要导出的知识库 ──────────────────────────────────────
            all_datasets = client.get_all_datasets(limit=100)
            logger.info(f"共获取到 {len(all_datasets)} 个知识库")

            if dataset_ids_raw:
                # 解析用户指定的 ID 列表（支持逗号 / 换行 / 空格分隔）
                requested_ids = {
                    i.strip()
                    for i in re.split(r"[,\n\r\s]+", dataset_ids_raw)
                    if i.strip()
                }
                selected = [d for d in all_datasets if d.get("id") in requested_ids]
                not_found = requested_ids - {d.get("id") for d in selected}
                if not_found:
                    logger.warning(f"以下知识库 ID 未找到: {not_found}")
            else:
                selected = all_datasets  # 默认全部

            if not selected:
                yield self.create_text_message(
                    "⚠️ 未找到任何知识库，请检查 dataset_ids 参数。"
                )
                return

            logger.info(f"将导出 {len(selected)} 个知识库")

            # ── 2. 逐个知识库打包 ZIP ───────────────────────────────────────
            total_file_count = 0
            failed_datasets = []
            dataset_results = []
            file_list_lines = []  # 汇总文件清单

            for dataset in selected:
                dataset_id = dataset.get("id")
                dataset_name = dataset.get("name", "unknown")
                safe_ds_name = _safe_name(dataset_name)

                logger.info(f"[{dataset_name}] 开始导出...")

                try:
                    documents = client.get_dataset_documents(dataset_id, limit=100)
                    logger.info(f"[{dataset_name}] 共 {len(documents)} 个文档")

                    if not documents:
                        file_list_lines.append(f"📂 {dataset_name}（无文档，跳过）")
                        dataset_results.append(
                            {
                                "dataset_id": dataset_id,
                                "dataset_name": dataset_name,
                                "status": "no_documents",
                                "exported_file_count": 0,
                            }
                        )
                        continue

                    # 在内存中建立 ZIP
                    zip_buf = io.BytesIO()
                    doc_file_list = []

                    with zipfile.ZipFile(
                        zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED
                    ) as zf:
                        for doc in documents:
                            doc_id = doc.get("id")
                            doc_name = doc.get("name", "unknown")
                            data_source_type = doc.get("data_source_type", "")
                            data_source_info = doc.get("data_source_info") or {}

                            file_added = False

                            # ── 尝试下载原始上传文件 ──
                            if data_source_type in {"upload_file", "file_upload"}:
                                file_bytes, mime = client.download_document_file(
                                    dataset_id, doc_id
                                )
                                if file_bytes:
                                    zip_path = _build_zip_entry_name(
                                        doc_name, mime or ""
                                    )
                                    zf.writestr(zip_path, file_bytes)
                                    doc_file_list.append(zip_path)
                                    file_added = True
                                    logger.info(
                                        f"  ✅ {doc_name} → {zip_path} ({len(file_bytes)} bytes, document download)"
                                    )

                            if not file_added and data_source_type in {
                                "upload_file",
                                "file_upload",
                            }:
                                upload_file_id = data_source_info.get(
                                    "upload_file_id"
                                ) or data_source_info.get("upload_file", {}).get("id")
                                if upload_file_id:
                                    file_bytes, mime = client.download_upload_file(
                                        upload_file_id
                                    )
                                    if file_bytes:
                                        # 确保 ZIP 内文件名不重复追加扩展名
                                        zip_path = _build_zip_entry_name(
                                            doc_name, mime or ""
                                        )
                                        zf.writestr(zip_path, file_bytes)
                                        doc_file_list.append(zip_path)
                                        file_added = True
                                        logger.info(
                                            f"  ✅ {doc_name} → {zip_path} ({len(file_bytes)} bytes, upload file fallback)"
                                        )

                            if not file_added:
                                logger.warning(
                                    f"  ⚠️ {doc_name} 无法获取文件内容，已跳过 (data_source_type={data_source_type or 'unknown'})"
                                )

                    zip_bytes = zip_buf.getvalue()
                    zip_filename = f"{safe_ds_name}-documents.zip"

                    if doc_file_list:
                        # 返回 ZIP blob
                        yield self.create_blob_message(
                            blob=zip_bytes,
                            meta={
                                "mime_type": "application/zip",
                                "filename": zip_filename,
                            },
                        )
                        total_file_count += len(doc_file_list)

                        # 收集文件清单
                        file_list_lines.append(f"📂 {dataset_name} → {zip_filename}")
                        for f in doc_file_list:
                            file_list_lines.append(f"   └─ {f}")
                        dataset_results.append(
                            {
                                "dataset_id": dataset_id,
                                "dataset_name": dataset_name,
                                "status": "exported",
                                "exported_file_count": len(doc_file_list),
                                "zip_filename": zip_filename,
                            }
                        )
                    else:
                        file_list_lines.append(
                            f"📂 {dataset_name}（所有文档均无法获取文件，已跳过）"
                        )
                        dataset_results.append(
                            {
                                "dataset_id": dataset_id,
                                "dataset_name": dataset_name,
                                "status": "no_exportable_files",
                                "exported_file_count": 0,
                            }
                        )

                except Exception as e:
                    logger.error(f"[{dataset_name}] 导出失败: {str(e)}")
                    failed_datasets.append(f"{dataset_name}: {str(e)}")
                    dataset_results.append(
                        {
                            "dataset_id": dataset_id,
                            "dataset_name": dataset_name,
                            "status": "failed",
                            "exported_file_count": 0,
                        }
                    )

            # ── 3. 返回汇总文本 ──────────────────────────────────────────────
            summary = f"✅ 知识库文件导出完成\n\n"
            summary += f"已处理知识库数: {len(selected)}\n"
            summary += f"总导出文件数: {total_file_count}\n\n"
            summary += "📋 文件清单:\n"
            summary += "\n".join(file_list_lines) if file_list_lines else "  （无）"

            if failed_datasets:
                summary += f"\n\n❌ 部分知识库处理失败:\n"
                for err in failed_datasets[:10]:
                    summary += f"  - {err}\n"
                if len(failed_datasets) > 10:
                    summary += f"  ... (共 {len(failed_datasets)} 个错误)"

            yield self.create_text_message(summary)

            # 同时返回 JSON 结构化清单
            yield self.create_json_message(
                {
                    "total_datasets": len(selected),
                    "total_files": total_file_count,
                    "datasets": dataset_results,
                }
            )

        except Exception as e:
            error_msg = f"Export Datasets failed: {str(e)}"
            logger.error(error_msg)
            yield self.create_text_message(error_msg)
