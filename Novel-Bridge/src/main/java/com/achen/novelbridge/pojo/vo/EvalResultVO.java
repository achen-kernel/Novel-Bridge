package com.achen.novelbridge.pojo.vo;

import java.util.List;
import java.util.Map;

/**
 * Individual evaluation result view object returned by result endpoints.
 * <p>
 * citations and scores are parsed from JSON strings stored in the entity.
 * </p>
 */
public class EvalResultVO {

    private Long id;
    private Long runId;
    private Long caseId;
    private String question;
    private String actualAnswer;
    private List<Object> citations;
    private Map<String, Object> scores;
    private String errorType;
    private String status;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getRunId() {
        return runId;
    }

    public void setRunId(Long runId) {
        this.runId = runId;
    }

    public Long getCaseId() {
        return caseId;
    }

    public void setCaseId(Long caseId) {
        this.caseId = caseId;
    }

    public String getQuestion() {
        return question;
    }

    public void setQuestion(String question) {
        this.question = question;
    }

    public String getActualAnswer() {
        return actualAnswer;
    }

    public void setActualAnswer(String actualAnswer) {
        this.actualAnswer = actualAnswer;
    }

    public List<Object> getCitations() {
        return citations;
    }

    public void setCitations(List<Object> citations) {
        this.citations = citations;
    }

    public Map<String, Object> getScores() {
        return scores;
    }

    public void setScores(Map<String, Object> scores) {
        this.scores = scores;
    }

    public String getErrorType() {
        return errorType;
    }

    public void setErrorType(String errorType) {
        this.errorType = errorType;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
