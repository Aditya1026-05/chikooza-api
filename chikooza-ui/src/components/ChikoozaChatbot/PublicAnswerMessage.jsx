import React from 'react';
import PropTypes from 'prop-types';

const normalizeDisplay = (payload = {}) => {
  const answer = payload.answer || '';
  const display = payload.display || {};

  if (display.kind === 'public_answer') {
    return {
      summary: display.summary || answer,
      items: Array.isArray(display.items) ? display.items : [],
      sources: Array.isArray(display.sources) ? display.sources : []
    };
  }

  const lines = String(answer)
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  const items = [];
  const summary = [];

  lines.forEach((line) => {
    const bullet = line.match(/^(?:[-*•]|\d+[.)])\s*(.+)$/);
    if (bullet) {
      items.push(bullet[1].trim());
    } else if (items.length) {
      items[items.length - 1] = `${items[items.length - 1]} ${line}`.trim();
    } else {
      summary.push(line);
    }
  });

  return {
    summary: summary.join(' ') || answer,
    items,
    sources: Array.isArray(payload.sources) ? payload.sources : []
  };
};

const sourceLabel = (source) => {
  if (!source?.source) {
    return '';
  }
  return source.page ? `${source.source} p.${source.page}` : source.source;
};

const PublicAnswerMessage = ({ payload }) => {
  const { summary, items, sources } = normalizeDisplay(payload);

  return (
    <div className="chikbot-answer-row">
      <div className="chikbot-answer-avatar" aria-hidden="true">C</div>
      <article className="chikbot-answer-card">
        {summary && <p className="chikbot-answer-summary">{summary}</p>}

        {items.length > 0 && (
          <ul className="chikbot-answer-list">
            {items.map((item, index) => (
              <li key={`${item}-${index}`}>{item}</li>
            ))}
          </ul>
        )}

        {sources.length > 0 && (
          <div className="chikbot-answer-sources" aria-label="Answer sources">
            <span>Sources</span>
            {sources.map((source, index) => {
              const label = sourceLabel(source);
              return label ? <small key={`${label}-${index}`}>{label}</small> : null;
            })}
          </div>
        )}
      </article>
    </div>
  );
};

PublicAnswerMessage.propTypes = {
  payload: PropTypes.shape({
    answer: PropTypes.string,
    display: PropTypes.object,
    sources: PropTypes.array
  })
};

export default PublicAnswerMessage;
