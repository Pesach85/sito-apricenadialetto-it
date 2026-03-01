<?php

defined('_JEXEC') or die;

use Joomla\CMS\Plugin\CMSPlugin;
use Joomla\CMS\Uri\Uri;

class plgContentMe_Edocs extends CMSPlugin
{
    protected $autoloadLanguage = true;

    public function onContentPrepare($context, &$item, &$params, $page = 0)
    {
        if ($context === 'com_finder.indexer') {
            return true;
        }

        $textRef = null;

        if (is_object($item) && property_exists($item, 'text')) {
            $textRef = &$item->text;
        } elseif (is_string($item)) {
            $textRef = &$item;
        } else {
            return true;
        }

        if (!is_string($textRef) || stripos($textRef, '{edocs}') === false) {
            return true;
        }

        $root = trim((string) $this->params->get('root', 'images/stories'), "/ \\t\\n\\r\\0\\x0B");
        $defaultWidth = (string) $this->params->get('width', '800');
        $defaultHeight = (string) $this->params->get('height', '1200');
        $downloadText = (string) $this->params->get('download_text', 'Download');

        $textRef = preg_replace_callback(
            '/\{edocs\}(.*?)\{\/edocs\}/is',
            function ($match) use ($root, $defaultWidth, $defaultHeight, $downloadText) {
                $parsed = $this->parseTagPayload((string) $match[1]);

                if (empty($parsed['path'])) {
                    return '';
                }

                $path = $this->buildDocumentUrl($parsed['path'], $root);

                $width = $this->normalizeSize($parsed['width'] ?? $defaultWidth, $defaultWidth);
                $height = $this->normalizeSize($parsed['height'] ?? $defaultHeight, $defaultHeight);

                $divClass = isset($parsed['div_class']) && $parsed['div_class'] !== ''
                    ? ' ' . htmlspecialchars((string) $parsed['div_class'], ENT_QUOTES, 'UTF-8')
                    : '';

                $divId = isset($parsed['div_id']) && $parsed['div_id'] !== ''
                    ? ' id="' . htmlspecialchars((string) $parsed['div_id'], ENT_QUOTES, 'UTF-8') . '"'
                    : '';

                $safePath = htmlspecialchars($path, ENT_QUOTES, 'UTF-8');
                $viewerSrc = 'https://docs.google.com/gview?url=' . rawurlencode($path) . '&embedded=true';

                $downloadLink = '';
                if (!empty($parsed['download']) && (string) $parsed['download'] !== '0') {
                    $label = (string) $parsed['download'] === 'link'
                        ? $downloadText
                        : (string) $parsed['download'];
                    $downloadLink = '<br /><br /><a href="' . $safePath . '" target="_blank" rel="noopener" class="edocs_link"><span class="edocs_link_text">' . htmlspecialchars($label, ENT_QUOTES, 'UTF-8') . '</span></a>';
                }

                return '<div class="edocs_viewer' . $divClass . '"' . $divId . '><iframe src="' . htmlspecialchars($viewerSrc, ENT_QUOTES, 'UTF-8') . '" style="width:' . htmlspecialchars($width, ENT_QUOTES, 'UTF-8') . '; height:' . htmlspecialchars($height, ENT_QUOTES, 'UTF-8') . ';" frameborder="0" class="edocs_iframe"></iframe>' . $downloadLink . '</div>';
            },
            $textRef
        );

        return true;
    }

    private function parseTagPayload(string $payload): array
    {
        $payload = trim($payload);

        if ($payload === '') {
            return [];
        }

        if (strpos($payload, '=') !== false) {
            $result = [];
            $pairs = preg_split('/\s*,\s*/', $payload);

            foreach ($pairs as $pair) {
                if ($pair === '' || strpos($pair, '=') === false) {
                    continue;
                }

                [$key, $value] = explode('=', $pair, 2);
                $key = trim($key);
                $value = trim($value);

                if ($key !== '') {
                    $result[$key] = $value;
                }
            }

            return $result;
        }

        $parts = array_map('trim', explode(',', $payload));

        return [
            'path' => $parts[0] ?? '',
            'width' => $parts[1] ?? '',
            'height' => $parts[2] ?? '',
            'download' => $parts[3] ?? '',
            'div_id' => $parts[4] ?? '',
        ];
    }

    private function buildDocumentUrl(string $path, string $root): string
    {
        $path = trim($path);

        if (preg_match('#^https?://#i', $path)) {
            return $path;
        }

        $base = rtrim(Uri::root(), '/');

        if (strpos($path, '/') === 0) {
            return $base . '/' . ltrim($path, '/');
        }

        if ($root !== '') {
            return $base . '/' . trim($root, '/') . '/' . ltrim($path, '/');
        }

        return $base . '/' . ltrim($path, '/');
    }

    private function normalizeSize(?string $value, string $fallback): string
    {
        $value = trim((string) $value);

        if ($value === '') {
            $value = trim($fallback);
        }

        if ($value === '') {
            return '800px';
        }

        if (preg_match('/\d(px|%)$/i', $value)) {
            return $value;
        }

        if (is_numeric($value)) {
            return $value . 'px';
        }

        return $fallback !== '' ? $fallback : '800px';
    }
}
