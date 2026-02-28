-- BACKUP DB prima di eseguire.

-- 1) Rimozione risorsa esterna non più raggiungibile
UPDATE #__content
SET introtext = REPLACE(introtext, 'http://images.web4web.it/w4w_190x60.jpg', ''),
    `fulltext`  = REPLACE(`fulltext`,  'http://images.web4web.it/w4w_190x60.jpg', '')
WHERE introtext LIKE '%images.web4web.it/w4w_190x60.jpg%'
   OR `fulltext`  LIKE '%images.web4web.it/w4w_190x60.jpg%';

UPDATE #__modules
SET content = REPLACE(content, 'http://images.web4web.it/w4w_190x60.jpg', '')
WHERE content LIKE '%images.web4web.it/w4w_190x60.jpg%';

UPDATE #__content
SET introtext = REPLACE(introtext, 'https://images.web4web.it/w4w_190x60.jpg', ''),
    `fulltext`  = REPLACE(`fulltext`,  'https://images.web4web.it/w4w_190x60.jpg', '')
WHERE introtext LIKE '%https://images.web4web.it/w4w_190x60.jpg%'
   OR `fulltext`  LIKE '%https://images.web4web.it/w4w_190x60.jpg%';

UPDATE #__modules
SET content = REPLACE(content, 'https://images.web4web.it/w4w_190x60.jpg', '')
WHERE content LIKE '%https://images.web4web.it/w4w_190x60.jpg%';

-- 2) Google Docs viewer -> HTTPS
UPDATE #__content
SET introtext = REPLACE(introtext, 'http://docs.google.com/gview?', 'https://docs.google.com/gview?'),
    `fulltext`  = REPLACE(`fulltext`,  'http://docs.google.com/gview?', 'https://docs.google.com/gview?')
WHERE introtext LIKE '%http://docs.google.com/gview?%'
   OR `fulltext`  LIKE '%http://docs.google.com/gview?%';

UPDATE #__modules
SET content = REPLACE(content, 'http://docs.google.com/gview?', 'https://docs.google.com/gview?')
WHERE content LIKE '%http://docs.google.com/gview?%';

-- 3) Facebook plugin URL legacy -> HTTPS
UPDATE #__modules
SET content = REPLACE(content, 'http://www.facebook.com/plugins/likebox.php', 'https://www.facebook.com/plugins/likebox.php')
WHERE content LIKE '%http://www.facebook.com/plugins/likebox.php%';
